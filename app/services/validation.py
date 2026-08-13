import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Customer, CustomerProductPrice, DraftOrder, Product
from app.schemas import PurchaseOrder, PurchaseOrderExtraction, ValidationResult
from app.services.rag import normalize

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


async def validate_authoritative_data(
    session: AsyncSession, order: PurchaseOrder, settings: Settings, run_id: str
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    customer = None
    if order.resolved_customer_id:
        customer = await session.get(Customer, order.resolved_customer_id)
    results.append(
        ValidationResult(
            code="CUSTOMER_RESOLVED",
            passed=customer is not None and customer.active,
            message=(
                f"Resolved customer {customer.canonical_name}"
                if customer
                else "Customer could not be resolved to an active record"
            ),
        )
    )

    if customer:
        supplied_address = normalize(order.shipping_address)
        address_passed = any(
            normalize(address) in supplied_address or supplied_address in normalize(address)
            for address in customer.approved_shipping_addresses
            if supplied_address
        )
        results.append(
            ValidationResult(
                code="APPROVED_SHIPPING_ADDRESS",
                passed=address_passed,
                message=(
                    "Shipping address matches an approved customer location"
                    if address_passed
                    else "Shipping address is not an approved customer location"
                ),
            )
        )

        expected_days = re.search(r"\d+", customer.payment_terms or "")
        supplied_days = re.search(r"\d+", order.payment_terms or "")
        terms_passed = bool(
            expected_days and supplied_days and expected_days.group() == supplied_days.group()
        )
        results.append(
            ValidationResult(
                code="PAYMENT_TERMS_MATCH",
                passed=terms_passed,
                message=(
                    f"Expected {customer.payment_terms}; "
                    f"received {order.payment_terms or 'missing'}"
                ),
            )
        )

    for index, item in enumerate(order.line_items, start=1):
        product = await session.get(Product, item.resolved_sku) if item.resolved_sku else None
        results.append(
            ValidationResult(
                code=f"LINE_{index}_PRODUCT_RESOLVED",
                passed=product is not None and product.active,
                message=(
                    f"Resolved to {product.sku} - {product.name}"
                    if product
                    else f"Line {index} could not be resolved to an active product"
                ),
            )
        )
        if customer and product and order.currency and item.unit_price is not None:
            contract = await session.scalar(
                select(CustomerProductPrice).where(
                    CustomerProductPrice.customer_id == customer.id,
                    CustomerProductPrice.sku == product.sku,
                    CustomerProductPrice.currency == order.currency,
                    CustomerProductPrice.active.is_(True),
                )
            )
            expected_price = contract.unit_price if contract else product.standard_unit_price
            if expected_price is not None:
                tolerance = expected_price * Decimal(str(settings.price_tolerance_percent / 100))
                price_passed = abs(item.unit_price - expected_price) <= tolerance
                results.append(
                    ValidationResult(
                        code=f"LINE_{index}_PRICE_MATCH",
                        passed=price_passed,
                        message=(
                            f"Expected {order.currency} {expected_price}; "
                            f"received {item.unit_price}"
                        ),
                    )
                )

    if customer and order.po_number:
        duplicate = await session.scalar(
            select(DraftOrder).where(
                DraftOrder.customer_id == customer.id,
                DraftOrder.po_number == order.po_number,
                DraftOrder.run_id != run_id,
            )
        )
        results.append(
            ValidationResult(
                code="UNIQUE_PO_NUMBER",
                passed=duplicate is None,
                message=(
                    "PO number has not previously been processed"
                    if duplicate is None
                    else f"PO number already exists as draft order {duplicate.id}"
                ),
            )
        )

    return results
