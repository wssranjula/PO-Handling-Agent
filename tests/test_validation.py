from datetime import date
from decimal import Decimal

from app.schemas import LineItem, PurchaseOrder
from app.services.validation import validate_purchase_order


def valid_order() -> PurchaseOrder:
    return PurchaseOrder(
        po_number="PO-10482",
        issue_date=date(2026, 8, 10),
        currency="USD",
        customer_name="Acme Retail",
        shipping_address="10 Main Street",
        subtotal=Decimal("4850.00"),
        tax=Decimal("0"),
        total=Decimal("4850.00"),
        line_items=[
            LineItem(
                line_number=1,
                raw_sku="BTL-BLU-16",
                raw_description="Blue insulated bottle 16oz",
                quantity=Decimal("100"),
                unit_price=Decimal("48.50"),
                line_total=Decimal("4850.00"),
            )
        ],
    )


def test_valid_order_passes_all_rules() -> None:
    assert all(result.passed for result in validate_purchase_order(valid_order()))


def test_total_mismatch_fails() -> None:
    order = valid_order().model_copy(update={"total": Decimal("4800")})
    failed = {result.code for result in validate_purchase_order(order) if not result.passed}
    assert "DOCUMENT_TOTAL_RECONCILES" in failed


def test_missing_line_value_routes_to_validation_failure() -> None:
    order = valid_order()
    order.line_items[0].unit_price = None
    failed = {result.code for result in validate_purchase_order(order) if not result.passed}
    assert "LINE_1_REQUIRED_UNIT_PRICE" in failed


def test_quantity_times_price_must_match_line_total() -> None:
    order = valid_order()
    order.line_items[0].unit_price = Decimal("40.00")
    failed = {result.code for result in validate_purchase_order(order) if not result.passed}
    assert "LINE_1_TOTAL_RECONCILES" in failed
