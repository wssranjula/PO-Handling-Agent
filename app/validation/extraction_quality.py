from app.schemas import PurchaseOrderExtraction, ValidationResult

CRITICAL_EVIDENCE_PATHS = (
    "order.po_number",
    "order.customer_name",
    "order.currency",
    "order.shipping_address",
    "order.total",
)


def validate_extraction_quality(
    extraction: PurchaseOrderExtraction, min_confidence: float
) -> list[ValidationResult]:
    results = [
        ValidationResult(
            code="IS_PURCHASE_ORDER",
            passed=extraction.document_is_purchase_order,
            message="The attachment must be identified as a purchase order",
        ),
        ValidationResult(
            code="EXTRACTION_CONFIDENCE",
            passed=extraction.overall_confidence >= min_confidence,
            message=(
                f"Extraction confidence {extraction.overall_confidence:.2f}; "
                f"required {min_confidence:.2f}"
            ),
        ),
        ValidationResult(
            code="NO_EXTRACTION_WARNINGS",
            passed=not extraction.warnings,
            message=(
                "No extraction warnings"
                if not extraction.warnings
                else "; ".join(warning.code for warning in extraction.warnings)
            ),
        ),
    ]
    evidence_by_path = {
        path: evidence
        for evidence in extraction.evidence
        for path in evidence.field_paths
        if evidence.confidence >= min_confidence
    }
    for path in CRITICAL_EVIDENCE_PATHS:
        results.append(
            ValidationResult(
                code=f"EVIDENCE_{path.removeprefix('order.').upper()}",
                passed=path in evidence_by_path,
                message=f"High-confidence source evidence required for {path}",
            )
        )
    for index, _ in enumerate(extraction.order.line_items):
        prefix = f"order.line_items[{index}]"
        supported = any(
            path == prefix or path.startswith(f"{prefix}.") for path in evidence_by_path
        )
        results.append(
            ValidationResult(
                code=f"EVIDENCE_LINE_ITEM_{index + 1}",
                passed=supported,
                message=f"High-confidence source evidence required for line item {index + 1}",
            )
        )
    return results
