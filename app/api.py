import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import close_database, get_session, initialize_database
from app.logging_config import bind_request_id, configure_logging, reset_request_id
from app.models import Customer, DraftOrder, ProcessingRun, ReviewCase, RunEnrichment
from app.schemas import IntakeResponse, ReviewDecision, ReviewRejection
from app.services.gmail import gmail_polling_loop, poll_gmail_once, stop_gmail_poller
from app.services.intake import ingest_email
from app.services.review import approve_review_case, reject_review_case

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info(
        "application_start env=%s tracing=%s langsmith_project=%s",
        settings.app_env,
        settings.langsmith_tracing,
        settings.langsmith_project,
    )
    await initialize_database()
    logger.info("database_initialized")
    application.state.gmail_task = None
    if settings.gmail_enabled:
        application.state.gmail_task = asyncio.create_task(
            gmail_polling_loop(settings), name="gmail-poller"
        )
    yield
    await stop_gmail_poller(application.state.gmail_task)
    await close_database()
    logger.info("application_stopped")


app = FastAPI(title="Purchase Order Intake Agent", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    token = bind_request_id(request_id)
    logger.info("request_started method=%s path=%s", request.method, request.url.path)
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        logger.info(
            "request_completed method=%s path=%s status=%s",
            request.method,
            request.url.path,
            response.status_code,
        )
        return response
    except Exception:
        logger.exception("request_failed method=%s path=%s", request.method, request.url.path)
        raise
    finally:
        reset_request_id(token)


@app.get("/health")
async def health(session: SessionDependency) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/integrations/gmail/status")
async def gmail_status() -> dict:
    current = get_settings()
    return {
        "enabled": current.gmail_enabled,
        "authorized": current.gmail_token_path.exists(),
        "credentials_configured": current.gmail_credentials_path.exists(),
        "poll_interval_seconds": current.gmail_poll_interval_seconds,
        "query": current.gmail_query,
    }


@app.post("/integrations/gmail/poll")
async def poll_gmail_now() -> dict[str, int]:
    try:
        return await poll_gmail_once(get_settings())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/webhooks/email", response_model=IntakeResponse, status_code=202)
async def receive_email(
    provider_message_id: Annotated[str, Form()],
    sender: Annotated[str, Form()],
    session: SessionDependency,
    subject: Annotated[str, Form()] = "",
    attachment: Annotated[UploadFile, File()] = ...,
) -> IntakeResponse:
    try:
        return await ingest_email(
            session=session,
            settings=get_settings(),
            provider_message_id=provider_message_id,
            sender=sender,
            subject=subject,
            attachment=attachment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/runs/{run_id}")
async def get_run(run_id: str, session: SessionDependency) -> dict:
    run = await session.scalar(select(ProcessingRun).where(ProcessingRun.id == run_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Processing run not found")
    enrichment = await session.scalar(select(RunEnrichment).where(RunEnrichment.run_id == run_id))
    draft = await session.scalar(select(DraftOrder).where(DraftOrder.run_id == run_id))
    return {
        "id": run.id,
        "status": run.status,
        "extracted_data": run.extracted_data,
        "validation_results": run.validation_results,
        "review_reasons": run.review_reasons,
        "enrichment": (
            {"resolved_order": enrichment.resolved_order, "matches": enrichment.matches}
            if enrichment
            else None
        ),
        "draft_order": (
            {"id": draft.id, "status": draft.status, "order_data": draft.order_data}
            if draft
            else None
        ),
        "error": run.error,
    }


def serialize_order(order: DraftOrder, customer_name: str | None = None) -> dict:
    return {
        "id": order.id,
        "run_id": order.run_id,
        "customer_id": order.customer_id,
        "customer_name": customer_name or order.order_data.get("customer_name"),
        "po_number": order.po_number,
        "currency": order.currency,
        "total": order.total,
        "status": order.status,
        "order_data": order.order_data,
        "created_at": order.created_at,
    }


@app.get("/orders")
async def list_orders(session: SessionDependency) -> list[dict]:
    rows = (
        await session.execute(
            select(DraftOrder, Customer.canonical_name)
            .join(Customer, Customer.id == DraftOrder.customer_id)
            .order_by(DraftOrder.created_at.desc())
        )
    ).all()
    return [serialize_order(order, customer_name) for order, customer_name in rows]


@app.get("/orders/{order_id}")
async def get_order(order_id: str, session: SessionDependency) -> dict:
    row = (
        await session.execute(
            select(DraftOrder, Customer.canonical_name)
            .join(Customer, Customer.id == DraftOrder.customer_id)
            .where(DraftOrder.id == order_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Draft order not found")
    return serialize_order(row[0], row[1])


@app.get("/reviews")
async def list_reviews(session: SessionDependency, status: str = "open") -> list[dict]:
    reviews = (
        await session.scalars(
            select(ReviewCase).where(ReviewCase.status == status).order_by(ReviewCase.created_at)
        )
    ).all()
    return [
        {
            "id": review.id,
            "run_id": review.run_id,
            "status": review.status,
            "reasons": review.reasons,
            "resolution": review.resolution,
            "created_at": review.created_at,
        }
        for review in reviews
    ]


@app.get("/reviews/{review_id}")
async def get_review(review_id: str, session: SessionDependency) -> dict:
    review = await session.get(ReviewCase, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review case not found")
    run = await session.get(ProcessingRun, review.run_id)
    enrichment = await session.scalar(
        select(RunEnrichment).where(RunEnrichment.run_id == review.run_id)
    )
    return {
        "id": review.id,
        "run_id": review.run_id,
        "status": review.status,
        "reasons": review.reasons,
        "resolution": review.resolution,
        "created_at": review.created_at,
        "extracted_data": run.extracted_data if run else None,
        "validation_results": run.validation_results if run else None,
        "error": run.error if run else None,
        "enrichment": (
            {"resolved_order": enrichment.resolved_order, "matches": enrichment.matches}
            if enrichment
            else None
        ),
    }


@app.post("/reviews/{review_id}/approve")
async def approve_review(
    review_id: str, decision: ReviewDecision, session: SessionDependency
) -> dict:
    review = await session.get(ReviewCase, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review case not found")
    try:
        return await approve_review_case(session, review, decision, get_settings())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/reviews/{review_id}/reject")
async def reject_review(
    review_id: str, rejection: ReviewRejection, session: SessionDependency
) -> dict:
    review = await session.get(ReviewCase, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review case not found")
    try:
        return await reject_review_case(session, review, rejection)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
