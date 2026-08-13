from decimal import Decimal

from app.schemas import PurchaseOrder, ValidationResult


def validate_purchase_order(order: PurchaseOrder) -> list[ValidationResult]:
    results: list[ValidationResult] = []

    required = {
        "po_number": order.po_number,
        "customer_name": order.customer_name,
        "currency": order.currency,
        "shipping_address": order.shipping_address,
        "total": order.total,
    }
    for field, value in required.items():
        is_present = value is not None and value != ""
        results.append(
            ValidationResult(
                code=f"REQUIRED_{field.upper()}",
                passed=is_present,
                message=f"{field} is {'present' if is_present else 'missing'}",
            )
        )

    results.append(
        ValidationResult(
            code="HAS_LINE_ITEMS",
            passed=bool(order.line_items),
            message="At least one line item is required",
        )
    )

    if order.line_items and order.subtotal is not None:
        computed = sum((item.line_total for item in order.line_items), Decimal("0"))
        results.append(
            ValidationResult(
                code="LINE_TOTALS_RECONCILE",
                passed=abs(computed - order.subtotal) <= Decimal("0.01"),
                message=f"Computed subtotal {computed}; stated subtotal {order.subtotal}",
            )
        )

    if order.subtotal is not None and order.total is not None:
        expected = order.subtotal + (order.tax or Decimal("0"))
        results.append(
            ValidationResult(
                code="DOCUMENT_TOTAL_RECONCILES",
                passed=abs(expected - order.total) <= Decimal("0.01"),
                message=f"Expected total {expected}; stated total {order.total}",
            )
        )

    return results
