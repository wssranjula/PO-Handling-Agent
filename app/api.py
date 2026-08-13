from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import close_database, get_session, initialize_database
from app.models import ProcessingRun
from app.schemas import IntakeResponse
from app.services.intake import ingest_email

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    await initialize_database()
    yield
    await close_database()


app = FastAPI(title="Purchase Order Intake Agent", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health(session: SessionDependency) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


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
    return {
        "id": run.id,
        "status": run.status,
        "extracted_data": run.extracted_data,
        "validation_results": run.validation_results,
        "review_reasons": run.review_reasons,
        "error": run.error,
    }
