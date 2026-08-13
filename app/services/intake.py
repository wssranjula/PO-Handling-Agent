import hashlib
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Attachment, EmailMessage, ProcessingRun, ProcessingStatus, ReviewCase
from app.schemas import IntakeResponse, Route
from app.workflow import workflow

ALLOWED_TYPES = {"application/pdf", "text/plain", "text/csv", "image/png", "image/jpeg"}


async def ingest_email(
    *,
    session: AsyncSession,
    settings: Settings,
    provider_message_id: str,
    sender: str,
    subject: str,
    attachment: UploadFile,
) -> IntakeResponse:
    existing = await session.scalar(
        select(EmailMessage).where(EmailMessage.provider_message_id == provider_message_id)
    )
    if existing:
        existing_attachment = await session.scalar(
            select(Attachment).where(Attachment.email_id == existing.id)
        )
        existing_run = None
        if existing_attachment:
            existing_run = await session.scalar(
                select(ProcessingRun).where(ProcessingRun.attachment_id == existing_attachment.id)
            )
        if existing_attachment and existing_run:
            return IntakeResponse(
                message_id=existing.id,
                attachment_id=existing_attachment.id,
                run_id=existing_run.id,
                status=existing_run.status,
            )

    content_type = attachment.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported attachment type: {content_type}")

    contents = await attachment.read(settings.max_attachment_bytes + 1)
    if len(contents) > settings.max_attachment_bytes:
        raise ValueError("Attachment exceeds configured size limit")
    if not contents:
        raise ValueError("Attachment is empty")

    email = EmailMessage(
        provider_message_id=provider_message_id,
        sender=sender,
        subject=subject,
    )
    session.add(email)
    await session.flush()

    digest = hashlib.sha256(contents).hexdigest()
    safe_name = Path(attachment.filename or "attachment").name
    storage_dir = settings.attachment_dir / email.id
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / f"{digest[:12]}-{safe_name}"
    storage_path.write_bytes(contents)

    stored = Attachment(
        email_id=email.id,
        filename=safe_name,
        content_type=content_type,
        size_bytes=len(contents),
        sha256=digest,
        storage_path=str(storage_path.resolve()),
    )
    session.add(stored)
    await session.flush()

    run = ProcessingRun(attachment_id=stored.id)
    session.add(run)
    await session.commit()

    try:
        result = await workflow.ainvoke(
            {
                "run_id": run.id,
                "attachment_path": stored.storage_path,
                "content_type": stored.content_type,
            }
        )
        run.extracted_data = result.get("extracted_order")
        run.validation_results = result.get("validation_results")
        run.review_reasons = result.get("review_reasons")
        if result["route"] == Route.AUTO_PROCESS:
            run.status = ProcessingStatus.AUTO_PROCESSED
        else:
            run.status = ProcessingStatus.NEEDS_REVIEW
            session.add(ReviewCase(run_id=run.id, reasons=run.review_reasons or []))
    except Exception as exc:
        run.status = ProcessingStatus.FAILED
        run.error = {"type": type(exc).__name__, "message": str(exc)}

    await session.commit()
    return IntakeResponse(
        message_id=email.id,
        attachment_id=stored.id,
        run_id=run.id,
        status=run.status,
    )
