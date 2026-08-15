from fastapi import APIRouter

from app.api_models import GmailPollResponse, GmailStatusResponse
from app.config import get_settings
from app.services.gmail import poll_gmail_once

router = APIRouter(prefix="/integrations/gmail", tags=["gmail"])


@router.get("/status", response_model=GmailStatusResponse)
async def gmail_status() -> GmailStatusResponse:
    settings = get_settings()
    return GmailStatusResponse(
        enabled=settings.gmail_enabled,
        authorized=settings.gmail_token_path.exists(),
        credentials_configured=settings.gmail_credentials_path.exists(),
        poll_interval_seconds=settings.gmail_poll_interval_seconds,
        query=settings.gmail_query,
    )


@router.post("/poll", response_model=GmailPollResponse)
async def poll_gmail_now() -> GmailPollResponse:
    return GmailPollResponse.model_validate(await poll_gmail_once(get_settings()))
