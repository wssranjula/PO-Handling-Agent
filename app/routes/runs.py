from fastapi import APIRouter

from app.api_models import RunResponse
from app.dependencies import SessionDependency
from app.services.queries import get_run_details

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, session: SessionDependency) -> dict:
    return await get_run_details(session, run_id)
