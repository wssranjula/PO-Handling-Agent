import re
from datetime import date
from decimal import Decimal

from app.schemas import LineItem, PurchaseOrder


class DevelopmentExtractor:
    """Deterministic adapter used until an LLM provider is configured.

    Keeping this behind a class boundary lets us replace it with structured LLM
    extraction without changing the graph.
    """

    async def extract(self, text: str) -> PurchaseOrder:
        values: dict[str, str] = {}
        items: list[LineItem] = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                values[key.strip().lower().replace(" ", "_")] = value.strip()
            elif line.lower().startswith("item|"):
                _, sku, description, quantity, unit_price = [
                    part.strip() for part in line.split("|")
                ]
                qty = Decimal(quantity)
                price = Decimal(unit_price)
                items.append(
                    LineItem(
                        line_number=len(items) + 1,
                        raw_sku=sku or None,
                        raw_description=description,
                        quantity=qty,
                        unit_price=price,
                        line_total=qty * price,
                    )
                )

        def decimal_value(name: str) -> Decimal | None:
            value = values.get(name)
            if value is None:
                return None
            return Decimal(re.sub(r"[^0-9.\-]", "", value))

        def date_value(name: str) -> date | None:
            value = values.get(name)
            return date.fromisoformat(value) if value else None

        subtotal = decimal_value("subtotal")
        if subtotal is None and items:
            subtotal = sum((item.line_total for item in items), Decimal("0"))
        tax = decimal_value("tax")
        total = decimal_value("total")
        if total is None and subtotal is not None:
            total = subtotal + (tax or Decimal("0"))

        return PurchaseOrder(
            po_number=values.get("po_number"),
            issue_date=date_value("issue_date"),
            currency=values.get("currency"),
            customer_name=values.get("customer"),
            shipping_address=values.get("shipping_address"),
            requested_delivery_date=date_value("requested_delivery_date"),
            payment_terms=values.get("payment_terms"),
            subtotal=subtotal,
            tax=tax,
            total=total,
            line_items=items,
        )
