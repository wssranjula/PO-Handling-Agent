from fastapi import APIRouter

from app.api_models import OrderResponse
from app.dependencies import SessionDependency
from app.services.queries import get_order_details, list_order_details

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderResponse])
async def list_orders(session: SessionDependency) -> list[dict]:
    return await list_order_details(session)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, session: SessionDependency) -> dict:
    return await get_order_details(session, order_id)
