from fastapi import APIRouter

from app.api_models import ReviewActionResponse, ReviewDetailResponse, ReviewSummaryResponse
from app.config import get_settings
from app.dependencies import SessionDependency
from app.errors import ResourceNotFoundError
from app.models import ReviewCase
from app.schemas import ReviewDecision, ReviewRejection
from app.services.queries import get_review_details, list_review_details
from app.services.review import approve_review_case, reject_review_case

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewSummaryResponse])
async def list_reviews(session: SessionDependency, status: str = "open") -> list[dict]:
    return await list_review_details(session, status)


@router.get("/{review_id}", response_model=ReviewDetailResponse)
async def get_review(review_id: str, session: SessionDependency) -> dict:
    return await get_review_details(session, review_id)


async def require_review(session: SessionDependency, review_id: str) -> ReviewCase:
    review = await session.get(ReviewCase, review_id)
    if review is None:
        raise ResourceNotFoundError("Review case not found")
    return review


@router.post("/{review_id}/approve", response_model=ReviewActionResponse)
async def approve_review(
    review_id: str, decision: ReviewDecision, session: SessionDependency
) -> dict:
    review = await require_review(session, review_id)
    return await approve_review_case(session, review, decision, get_settings())


@router.post("/{review_id}/reject", response_model=ReviewActionResponse)
async def reject_review(
    review_id: str, rejection: ReviewRejection, session: SessionDependency
) -> dict:
    review = await require_review(session, review_id)
    return await reject_review_case(session, review, rejection)
