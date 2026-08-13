from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import DraftOrder, ProcessingRun, ProcessingStatus, ReviewCase, RunEnrichment
from app.schemas import PurchaseOrder, ReviewDecision, ReviewRejection
from app.services.rag import RAGService
from app.services.validation import validate_authoritative_data, validate_purchase_order


def recalculate_review_totals(order: PurchaseOrder) -> PurchaseOrder:
    """Treat quantity, unit price, and tax as inputs; all totals are derived values."""
    corrected = order.model_copy(deep=True)
    for item in corrected.line_items:
        if item.quantity is not None and item.unit_price is not None:
            item.line_total = item.quantity * item.unit_price
    if corrected.line_items and all(item.line_total is not None for item in corrected.line_items):
        corrected.subtotal = sum(
            (item.line_total for item in corrected.line_items if item.line_total is not None),
            start=Decimal("0"),
        )
        corrected.total = corrected.subtotal + (corrected.tax or Decimal("0"))
    return corrected


async def approve_review_case(
    session: AsyncSession,
    review: ReviewCase,
    decision: ReviewDecision,
    settings: Settings,
) -> dict:
    if review.status != "open":
        raise ValueError("Review case is not open")
    run = await session.get(ProcessingRun, review.run_id)
    if run is None:
        raise ValueError("Processing run not found")

    corrected_order = recalculate_review_totals(decision.corrected_order)
    enrichment = await RAGService(settings).enrich(session, corrected_order)
    results = [
        *validate_purchase_order(enrichment.order),
        *await validate_authoritative_data(session, enrichment.order, settings, run.id),
    ]
    failed = [result.code for result in results if not result.passed]

    stored_enrichment = await session.scalar(
        select(RunEnrichment).where(RunEnrichment.run_id == run.id)
    )
    if stored_enrichment is None:
        stored_enrichment = RunEnrichment(
            run_id=run.id,
            resolved_order=enrichment.order.model_dump(mode="json"),
            matches=[match.model_dump(mode="json") for match in enrichment.matches],
        )
        session.add(stored_enrichment)
    else:
        stored_enrichment.resolved_order = enrichment.order.model_dump(mode="json")
        stored_enrichment.matches = [match.model_dump(mode="json") for match in enrichment.matches]

    run.validation_results = [result.model_dump(mode="json") for result in results]
    run.review_reasons = failed
    review.reasons = failed
    review.resolution = {
        "action": "approved",
        "reviewer": decision.reviewer,
        "notes": decision.notes,
        "corrected_order": corrected_order.model_dump(mode="json"),
    }

    if failed:
        await session.commit()
        return {"status": "needs_review", "review_reasons": failed, "draft_order_id": None}

    order = enrichment.order
    draft = DraftOrder(
        run_id=run.id,
        customer_id=order.resolved_customer_id,
        po_number=order.po_number,
        currency=order.currency,
        total=order.total,
        order_data=order.model_dump(mode="json"),
    )
    session.add(draft)
    review.status = "approved"
    run.status = ProcessingStatus.AUTO_PROCESSED
    await session.commit()
    return {"status": "approved", "review_reasons": [], "draft_order_id": draft.id}


async def reject_review_case(
    session: AsyncSession,
    review: ReviewCase,
    rejection: ReviewRejection,
) -> dict:
    if review.status != "open":
        raise ValueError("Review case is not open")
    run = await session.get(ProcessingRun, review.run_id)
    if run is None:
        raise ValueError("Processing run not found")

    review.status = "rejected"
    review.resolution = {
        "action": "rejected",
        "reviewer": rejection.reviewer,
        "reason": rejection.reason,
    }
    run.status = ProcessingStatus.REJECTED
    await session.commit()
    return {"status": "rejected", "review_id": review.id, "run_id": run.id}
