import asyncio
import base64
import hashlib
import logging
from contextlib import suppress
from email.utils import parseaddr
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import select
from starlette.datastructures import Headers

from app.config import Settings
from app.db import SessionFactory
from app.models import EmailMessage
from app.services.intake import ingest_email

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
SUPPORTED_GMAIL_ATTACHMENTS = {"application/pdf", "text/plain", "text/csv"}
logger = logging.getLogger(__name__)
poll_lock = asyncio.Lock()


def decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def iter_message_parts(payload: dict[str, Any]):
    for part in payload.get("parts", []):
        yield from iter_message_parts(part)
    if payload.get("filename"):
        yield payload


def message_headers(payload: dict[str, Any]) -> dict[str, str]:
    return {
        header["name"].lower(): header.get("value", "")
        for header in payload.get("headers", [])
    }


def gmail_provider_id(message_id: str, part: dict[str, Any]) -> str:
    """Build a stable ID that fits the database's 255-character provider ID column."""
    part_id = part.get("partId")
    if not part_id:
        attachment_id = part.get("body", {}).get("attachmentId", "")
        part_id = hashlib.sha256(attachment_id.encode()).hexdigest()[:16]
    return f"gmail:{message_id}:{part_id}"


def load_gmail_credentials(settings: Settings) -> Credentials:
    token_path = settings.gmail_token_path
    if not token_path.exists():
        raise RuntimeError(
            f"Gmail token not found at {token_path}. Run scripts/gmail_authorize.py first."
        )
    credentials = Credentials.from_authorized_user_file(str(token_path), GMAIL_SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
    if not credentials.valid:
        raise RuntimeError("Gmail OAuth credentials are invalid or have been revoked")
    return credentials


def build_gmail_service(settings: Settings):
    return build(
        "gmail",
        "v1",
        credentials=load_gmail_credentials(settings),
        cache_discovery=False,
    )


async def execute_google(request):
    return await asyncio.to_thread(request.execute)


async def attachment_bytes(service, message_id: str, part: dict[str, Any]) -> bytes:
    body = part.get("body", {})
    if body.get("data"):
        return decode_base64url(body["data"])
    attachment_id = body.get("attachmentId")
    if not attachment_id:
        return b""
    result = await execute_google(
        service.users()
        .messages()
        .attachments()
        .get(userId="me", messageId=message_id, id=attachment_id)
    )
    return decode_base64url(result.get("data", ""))


async def gmail_attachment_already_ingested(provider_message_id: str) -> bool:
    async with SessionFactory() as session:
        result = await session.scalar(
            select(EmailMessage.id).where(
                EmailMessage.provider_message_id == provider_message_id
            )
        )
        return result is not None


async def _poll_gmail_once(settings: Settings, service=None) -> dict[str, int]:
    service = service or await asyncio.to_thread(build_gmail_service, settings)
    response = await execute_google(
        service.users()
        .messages()
        .list(
            userId="me",
            q=settings.gmail_query,
            maxResults=settings.gmail_max_messages_per_poll,
        )
    )
    stats = {
        "messages": 0,
        "attachments": 0,
        "ingested": 0,
        "failed": 0,
        "duplicates": 0,
        "skipped": 0,
    }
    for reference in response.get("messages", []):
        message_id = reference["id"]
        message = await execute_google(
            service.users().messages().get(userId="me", id=message_id, format="full")
        )
        stats["messages"] += 1
        payload = message.get("payload", {})
        headers = message_headers(payload)
        sender = parseaddr(headers.get("from", ""))[1] or headers.get("from", "unknown")
        subject = headers.get("subject", "")

        for part in iter_message_parts(payload):
            mime_type = part.get("mimeType", "application/octet-stream").lower()
            if mime_type not in SUPPORTED_GMAIL_ATTACHMENTS:
                stats["skipped"] += 1
                continue
            stats["attachments"] += 1
            provider_id = gmail_provider_id(message_id, part)
            if await gmail_attachment_already_ingested(provider_id):
                stats["duplicates"] += 1
                continue
            contents = await attachment_bytes(service, message_id, part)
            if not contents:
                stats["skipped"] += 1
                continue
            upload = UploadFile(
                file=BytesIO(contents),
                filename=Path(part["filename"]).name,
                headers=Headers({"content-type": mime_type}),
            )
            try:
                async with SessionFactory() as session:
                    result = await ingest_email(
                        session=session,
                        settings=settings,
                        provider_message_id=provider_id,
                        sender=sender,
                        subject=subject,
                        attachment=upload,
                    )
                stats["ingested"] += 1
                if result.status == "failed":
                    stats["failed"] += 1
            finally:
                await upload.close()

    logger.info("gmail_poll_completed stats=%s", stats)
    return stats


async def poll_gmail_once(settings: Settings, service=None) -> dict[str, int]:
    async with poll_lock:
        return await _poll_gmail_once(settings, service)


async def gmail_polling_loop(settings: Settings) -> None:
    logger.info(
        "gmail_poller_started interval_seconds=%s query=%s",
        settings.gmail_poll_interval_seconds,
        settings.gmail_query,
    )
    while True:
        try:
            await poll_gmail_once(settings)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("gmail_poll_failed")
        await asyncio.sleep(settings.gmail_poll_interval_seconds)


async def stop_gmail_poller(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
