from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DraftOrder, ProcessingRun, ProcessingStatus, ReviewCase, RunEnrichment
from app.schemas import PurchaseOrder, Route


async def apply_processing_outcome(
    session: AsyncSession,
    run: ProcessingRun,
    result: dict[str, Any],
) -> None:
    """Stage a complete workflow outcome; the caller owns the transaction commit."""
    run.extracted_data = result.get("extraction")
    run.validation_results = result.get("validation_results")
    run.review_reasons = result.get("review_reasons")

    enrichment_data = result.get("enrichment")
    if enrichment_data:
        session.add(
            RunEnrichment(
                run_id=run.id,
                resolved_order=enrichment_data["order"],
                matches=enrichment_data["matches"],
            )
        )

    if result["route"] == Route.HUMAN_REVIEW:
        run.status = ProcessingStatus.NEEDS_REVIEW
        session.add(ReviewCase(run_id=run.id, reasons=run.review_reasons or []))
        return

    order = PurchaseOrder.model_validate(result["extracted_order"])
    if not order.resolved_customer_id or not order.po_number or not order.currency:
        raise ValueError("Auto-processed order is missing draft-order identifiers")
    if order.total is None:
        raise ValueError("Auto-processed order is missing a total")
    session.add(
        DraftOrder(
            run_id=run.id,
            customer_id=order.resolved_customer_id,
            po_number=order.po_number,
            currency=order.currency,
            total=order.total,
            order_data=order.model_dump(mode="json"),
        )
    )
    run.status = ProcessingStatus.AUTO_PROCESSED
