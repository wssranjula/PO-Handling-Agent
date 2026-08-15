from fastapi import APIRouter
from sqlalchemy import text

from app.api_models import HealthResponse
from app.dependencies import SessionDependency

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(session: SessionDependency) -> HealthResponse:
    await session.execute(text("SELECT 1"))
    return HealthResponse(status="ok")
