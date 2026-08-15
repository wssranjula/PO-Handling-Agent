import hashlib
import logging
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.errors import InvalidAttachmentError
from app.models import (
    Attachment,
    EmailMessage,
    ProcessingRun,
    ProcessingStatus,
)
from app.schemas import IntakeResponse
from app.services.outcomes import apply_processing_outcome
from app.workflow import get_workflow

ALLOWED_TYPES = {"application/pdf", "text/plain", "text/csv", "image/png", "image/jpeg"}
logger = logging.getLogger(__name__)


async def ingest_email(
    *,
    session: AsyncSession,
    settings: Settings,
    provider_message_id: str,
    sender: str,
    subject: str,
    attachment: UploadFile,
    provider_attachment_id: str | None = None,
    workflow_graph=None,
) -> IntakeResponse:
    logger.info(
        "email_intake_started provider_message_id=%s filename=%s content_type=%s",
        provider_message_id,
        attachment.filename,
        attachment.content_type,
    )
    existing = await session.scalar(
        select(EmailMessage).where(EmailMessage.provider_message_id == provider_message_id)
    )
    if existing:
        attachment_query = select(Attachment).where(Attachment.email_id == existing.id)
        if provider_attachment_id:
            attachment_query = attachment_query.where(
                Attachment.provider_attachment_id == provider_attachment_id
            )
        existing_attachment = await session.scalar(attachment_query)
        existing_run = None
        if existing_attachment:
            existing_run = await session.scalar(
                select(ProcessingRun).where(ProcessingRun.attachment_id == existing_attachment.id)
            )
        if existing_attachment and existing_run:
            logger.info(
                "email_intake_duplicate provider_message_id=%s run_id=%s status=%s",
                provider_message_id,
                existing_run.id,
                existing_run.status,
            )
            return IntakeResponse(
                message_id=existing.id,
                attachment_id=existing_attachment.id,
                run_id=existing_run.id,
                status=existing_run.status,
            )

    content_type = attachment.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        raise InvalidAttachmentError(f"Unsupported attachment type: {content_type}")

    contents = await attachment.read(settings.max_attachment_bytes + 1)
    if len(contents) > settings.max_attachment_bytes:
        raise InvalidAttachmentError("Attachment exceeds configured size limit")
    if not contents:
        raise InvalidAttachmentError("Attachment is empty")

    email = existing
    if email is None:
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
    logger.info(
        "attachment_stored email_id=%s filename=%s bytes=%s sha256_prefix=%s",
        email.id,
        safe_name,
        len(contents),
        digest[:12],
    )

    stored = Attachment(
        email_id=email.id,
        provider_attachment_id=provider_attachment_id,
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
    logger.info("processing_run_created run_id=%s attachment_id=%s", run.id, stored.id)

    try:
        graph = workflow_graph or get_workflow()
        result = await graph.ainvoke(
            {
                "run_id": run.id,
                "attachment_path": stored.storage_path,
                "content_type": stored.content_type,
            },
            config={
                "run_name": "purchase_order_intake",
                "tags": ["po-intake", settings.app_env],
                "metadata": {
                    "processing_run_id": run.id,
                    "attachment_id": stored.id,
                    "provider_message_id": provider_message_id,
                },
            },
        )
        await apply_processing_outcome(session, run, result)
        logger.info(
            "processing_run_completed run_id=%s status=%s review_reasons=%s",
            run.id,
            run.status,
            run.review_reasons or [],
        )
    except Exception as exc:
        run.status = ProcessingStatus.FAILED
        run.error = {"type": type(exc).__name__, "message": str(exc)}
        logger.exception(
            "processing_run_failed run_id=%s error_type=%s", run.id, type(exc).__name__
        )

    await session.commit()
    return IntakeResponse(
        message_id=email.id,
        attachment_id=stored.id,
        run_id=run.id,
        status=run.status,
    )
