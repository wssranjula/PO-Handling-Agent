from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ResourceNotFoundError
from app.models import Customer, DraftOrder, ProcessingRun, ReviewCase, RunEnrichment


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


async def get_run_details(session: AsyncSession, run_id: str) -> dict:
    run = await session.get(ProcessingRun, run_id)
    if run is None:
        raise ResourceNotFoundError("Processing run not found")
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


async def list_order_details(session: AsyncSession) -> list[dict]:
    rows = (
        await session.execute(
            select(DraftOrder, Customer.canonical_name)
            .join(Customer, Customer.id == DraftOrder.customer_id)
            .order_by(DraftOrder.created_at.desc())
        )
    ).all()
    return [serialize_order(order, customer_name) for order, customer_name in rows]


async def get_order_details(session: AsyncSession, order_id: str) -> dict:
    row = (
        await session.execute(
            select(DraftOrder, Customer.canonical_name)
            .join(Customer, Customer.id == DraftOrder.customer_id)
            .where(DraftOrder.id == order_id)
        )
    ).one_or_none()
    if row is None:
        raise ResourceNotFoundError("Draft order not found")
    return serialize_order(row[0], row[1])


async def list_review_details(session: AsyncSession, status: str) -> list[dict]:
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


async def get_review_details(session: AsyncSession, review_id: str) -> dict:
    review = await session.get(ReviewCase, review_id)
    if review is None:
        raise ResourceNotFoundError("Review case not found")
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
