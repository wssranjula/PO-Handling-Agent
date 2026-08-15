from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from app.config import get_settings
from app.dependencies import SessionDependency
from app.schemas import IntakeResponse
from app.services.intake import ingest_email

router = APIRouter(tags=["intake"])


@router.post("/webhooks/email", response_model=IntakeResponse, status_code=202)
async def receive_email(
    provider_message_id: Annotated[str, Form()],
    sender: Annotated[str, Form()],
    attachment: Annotated[UploadFile, File()],
    session: SessionDependency,
    subject: Annotated[str, Form()] = "",
) -> IntakeResponse:
    return await ingest_email(
        session=session,
        settings=get_settings(),
        provider_message_id=provider_message_id,
        sender=sender,
        subject=subject,
        attachment=attachment,
    )
