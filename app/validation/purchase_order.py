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
    for index, item in enumerate(order.line_items, start=1):
        required_item_fields = {
            "DESCRIPTION": item.raw_description,
            "QUANTITY": item.quantity,
            "UNIT_PRICE": item.unit_price,
            "LINE_TOTAL": item.line_total,
        }
        for field, value in required_item_fields.items():
            results.append(
                ValidationResult(
                    code=f"LINE_{index}_REQUIRED_{field}",
                    passed=value is not None and value != "",
                    message=f"Line {index} requires {field.lower().replace('_', ' ')}",
                )
            )
        if (
            item.quantity is not None
            and item.unit_price is not None
            and item.line_total is not None
        ):
            expected_line_total = item.quantity * item.unit_price
            results.append(
                ValidationResult(
                    code=f"LINE_{index}_TOTAL_RECONCILES",
                    passed=abs(expected_line_total - item.line_total) <= Decimal("0.01"),
                    message=(
                        f"Line {index} expected total {expected_line_total}; "
                        f"stated total {item.line_total}"
                    ),
                )
            )
    line_totals = [item.line_total for item in order.line_items]
    if (
        order.line_items
        and order.subtotal is not None
        and all(value is not None for value in line_totals)
    ):
        computed = sum((value for value in line_totals if value is not None), Decimal("0"))
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
