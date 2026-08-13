from decimal import Decimal

from app.schemas import LineItem, PurchaseOrder
from app.services.review import recalculate_review_totals


def test_review_recalculates_all_derived_totals() -> None:
    order = PurchaseOrder(
        po_number="PO-PRICE-FIX",
        currency="USD",
        customer_name="Northstar Home Stores",
        shipping_address="Warehouse 4",
        subtotal=Decimal("90"),
        tax=Decimal("0"),
        total=Decimal("90"),
        line_items=[
            LineItem(
                line_number=1,
                raw_description="White mug",
                quantity=Decimal("10"),
                unit_price=Decimal("7.50"),
                line_total=Decimal("90"),
            )
        ],
    )

    corrected = recalculate_review_totals(order)

    assert corrected.line_items[0].line_total == Decimal("75.00")
    assert corrected.subtotal == Decimal("75.00")
    assert corrected.total == Decimal("75.00")
