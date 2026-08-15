from decimal import Decimal

import pytest

from app.models import DraftOrder, ProcessingRun, ProcessingStatus, ReviewCase, RunEnrichment
from app.services.outcomes import apply_processing_outcome


class RecordingSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, value) -> None:
        self.added.append(value)


def run_record() -> ProcessingRun:
    return ProcessingRun(id="run-1", attachment_id="attachment-1")


def enrichment_order() -> dict:
    return {
        "po_number": "PO-1",
        "issue_date": "2026-08-14",
        "currency": "USD",
        "customer_name": "Acme Retail",
        "resolved_customer_id": "CUST-ACME",
        "shipping_address": "Dock 2, 55 Lake Avenue, Kandy, Sri Lanka",
        "requested_delivery_date": None,
        "payment_terms": "Net 30",
        "subtotal": "75.00",
        "tax": "0",
        "total": "75.00",
        "line_items": [
            {
                "line_number": 1,
                "raw_description": "White mug",
                "raw_sku": "MUG-WHT",
                "resolved_sku": "MUG-WHITE-STD",
                "quantity": "10",
                "unit_price": "7.50",
                "line_total": "75.00",
            }
        ],
    }


@pytest.mark.asyncio
async def test_auto_process_stages_enrichment_and_draft_without_committing() -> None:
    session = RecordingSession()
    run = run_record()
    order = enrichment_order()

    await apply_processing_outcome(
        session,
        run,
        {
            "route": "auto_process",
            "extraction": {"order": order},
            "extracted_order": order,
            "enrichment": {"order": order, "matches": []},
            "validation_results": [],
            "review_reasons": [],
        },
    )

    assert run.status == ProcessingStatus.AUTO_PROCESSED
    assert any(isinstance(value, RunEnrichment) for value in session.added)
    draft = next(value for value in session.added if isinstance(value, DraftOrder))
    assert draft.total == Decimal("75.00")


@pytest.mark.asyncio
async def test_review_outcome_stages_review_case_without_draft() -> None:
    session = RecordingSession()
    run = run_record()
    order = enrichment_order()

    await apply_processing_outcome(
        session,
        run,
        {
            "route": "human_review",
            "extraction": {"order": order},
            "extracted_order": order,
            "enrichment": {"order": order, "matches": []},
            "validation_results": [],
            "review_reasons": ["PRICE_MATCH"],
        },
    )

    assert run.status == ProcessingStatus.NEEDS_REVIEW
    assert any(isinstance(value, ReviewCase) for value in session.added)
    assert not any(isinstance(value, DraftOrder) for value in session.added)
