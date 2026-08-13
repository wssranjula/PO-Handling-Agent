from app.schemas import PurchaseOrderExtraction
from app.services.validation import validate_extraction_quality


def test_low_confidence_and_missing_evidence_fail_quality_gate() -> None:
    extraction = PurchaseOrderExtraction.model_validate(
        {
            "document_is_purchase_order": True,
            "order": {
                "po_number": "PO-1",
                "customer_name": "Acme",
                "currency": "USD",
                "shipping_address": "Main Street",
                "total": "10",
                "line_items": [],
            },
            "evidence": [],
            "warnings": [{"code": "AMBIGUOUS_TOTAL", "message": "Two totals were visible"}],
            "overall_confidence": 0.6,
        }
    )

    failed = {
        result.code
        for result in validate_extraction_quality(extraction, min_confidence=0.85)
        if not result.passed
    }

    assert "EXTRACTION_CONFIDENCE" in failed
    assert "NO_EXTRACTION_WARNINGS" in failed
    assert "EVIDENCE_PO_NUMBER" in failed
