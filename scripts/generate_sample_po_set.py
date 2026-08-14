from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT_DIR = Path("output/pdf")


@dataclass(frozen=True)
class Item:
    sku: str
    description: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def total(self) -> Decimal:
        return self.quantity * self.unit_price


@dataclass(frozen=True)
class PurchaseOrder:
    filename: str
    customer: str
    customer_tagline: str
    po_number: str
    issue_date: str
    delivery_date: str
    currency: str
    payment_terms: str
    shipping_address: str
    buyer: str
    buyer_email: str
    accent: str
    items: tuple[Item, ...]
    notes: str


ORDERS = (
    PurchaseOrder(
        filename="po-01-clean-northstar.pdf",
        customer="NORTHSTAR HOME STORES",
        customer_tagline="Retail Procurement Division",
        po_number="NS-2026-810",
        issue_date="14 Aug 2026",
        delivery_date="29 Aug 2026",
        currency="USD",
        payment_terms="Net 45",
        shipping_address=(
            "Northstar Home Stores - Central Warehouse<br/>"
            "Warehouse 4, 18 Harbour Road<br/>Colombo 01, Sri Lanka<br/>"
            "Attention: Receiving Desk"
        ),
        buyer="Maya Perera, Procurement Manager",
        buyer_email="purchasing@northstar.test",
        accent="#176B4D",
        items=(
            Item(
                "blue-therm16",
                "Blue insulated drink bottle - 16 oz",
                Decimal("12"),
                Decimal("18.50"),
            ),
            Item(
                "lid spare",
                "Replacement lid for 16 oz insulated bottle",
                Decimal("25"),
                Decimal("2.00"),
            ),
        ),
        notes="Deliver on weekdays between 08:00 and 15:00. No partial shipments.",
    ),
    PurchaseOrder(
        filename="po-02-price-mismatch-review.pdf",
        customer="NORTHSTAR HOME STORES",
        customer_tagline="Seasonal Replenishment Team",
        po_number="NS-2026-811",
        issue_date="14 Aug 2026",
        delivery_date="02 Sep 2026",
        currency="USD",
        payment_terms="Net 45 days",
        shipping_address=(
            "Northstar Home Stores - Central Warehouse<br/>"
            "Warehouse 4, 18 Harbour Road<br/>Colombo 01, Sri Lanka<br/>"
            "Attention: Receiving Desk"
        ),
        buyer="Ravi Fernando, Category Buyer",
        buyer_email="ravi.fernando@northstar.test",
        accent="#A85B20",
        items=(Item("MUG-WHT", "White ceramic mug, retail boxed", Decimal("10"), Decimal("9.00")),),
        notes="Promotional replenishment. Unit price shown is the buyer-submitted amount.",
    ),
    PurchaseOrder(
        filename="po-03-unknown-sku-review.pdf",
        customer="ACME RETAIL LTD",
        customer_tagline="Store Operations Purchasing",
        po_number="ACME-PO-4407",
        issue_date="14 Aug 2026",
        delivery_date="05 Sep 2026",
        currency="USD",
        payment_terms="Net 30",
        shipping_address=(
            "Acme Retail - Kandy Receiving<br/>Dock 2, 55 Lake Avenue<br/>"
            "Kandy, Sri Lanka<br/>Attention: Stores Team"
        ),
        buyer="Nadeesha Silva, Purchasing Officer",
        buyer_email="orders@acmeretail.test",
        accent="#315B91",
        items=(
            Item(
                "TOTE-ECO-XL",
                "Extra-large recycled canvas shopping tote",
                Decimal("20"),
                Decimal("6.25"),
            ),
        ),
        notes=(
            "New product trial. Please contact the buyer if the item reference is not "
            "recognized."
        ),
    ),
)


def amount(value: Decimal) -> str:
    return f"{value:,.2f}"


def build_order(order: PurchaseOrder) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / order.filename
    accent = colors.HexColor(order.accent)
    ink = colors.HexColor("#18231E")
    muted = colors.HexColor("#64706A")
    border = colors.HexColor("#D7DDD9")
    wash = colors.HexColor("#F2F5F3")

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Brand", fontName="Helvetica-Bold", fontSize=18, leading=21, textColor=ink
        )
    )
    styles.add(
        ParagraphStyle(
            name="Muted", fontName="Helvetica", fontSize=8.5, leading=12, textColor=muted
        )
    )
    styles.add(
        ParagraphStyle(
            name="Label",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=muted,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(name="Value", fontName="Helvetica", fontSize=9.5, leading=13, textColor=ink)
    )
    styles.add(ParagraphStyle(name="Right", parent=styles["Value"], alignment=TA_RIGHT))
    styles.add(
        ParagraphStyle(
            name="Section", fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=accent
        )
    )
    styles.add(
        ParagraphStyle(name="Small", fontName="Helvetica", fontSize=8, leading=11, textColor=ink)
    )

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Purchase Order {order.po_number}",
        author=order.customer.title(),
    )

    header = Table(
        [
            [
                Paragraph(
                    f"{order.customer}<br/>"
                    f"<font size='9' color='#64706A'>{order.customer_tagline}</font>",
                    styles["Brand"],
                ),
                Paragraph(
                    "<font size='20'><b>PURCHASE ORDER</b></font><br/>"
                    "<font size='8' color='#64706A'>Supplier copy</font>",
                    styles["Right"],
                ),
            ]
        ],
        colWidths=[108 * mm, 69 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    meta = Table(
        [
            [
                Paragraph("PO NUMBER", styles["Label"]),
                Paragraph(order.po_number, styles["Value"]),
                Paragraph("ISSUE DATE", styles["Label"]),
                Paragraph(order.issue_date, styles["Value"]),
            ],
            [
                Paragraph("CURRENCY", styles["Label"]),
                Paragraph(order.currency, styles["Value"]),
                Paragraph("REQUESTED DELIVERY", styles["Label"]),
                Paragraph(order.delivery_date, styles["Value"]),
            ],
            [
                Paragraph("CUSTOMER", styles["Label"]),
                Paragraph(order.customer.title(), styles["Value"]),
                Paragraph("PAYMENT TERMS", styles["Label"]),
                Paragraph(order.payment_terms, styles["Value"]),
            ],
        ],
        colWidths=[29 * mm, 59 * mm, 36 * mm, 53 * mm],
    )
    meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), wash),
                ("GRID", (0, 0), (-1, -1), 0.45, border),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    address = Table(
        [
            [Paragraph("SUPPLIER", styles["Section"]), Paragraph("SHIP TO", styles["Section"])],
            [
                Paragraph(
                    "<b>Example Distribution Company (Pvt) Ltd</b><br/>"
                    "142 Galle Road<br/>Colombo 03, Sri Lanka<br/>"
                    "sales@example-distribution.test",
                    styles["Value"],
                ),
                Paragraph(order.shipping_address, styles["Value"]),
            ],
        ],
        colWidths=[88.5 * mm, 88.5 * mm],
    )
    address.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), wash),
                ("BOX", (0, 0), (0, -1), 0.55, border),
                ("BOX", (1, 0), (1, -1), 0.55, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    item_rows = [["LINE", "ITEM REFERENCE", "DESCRIPTION", "QTY", "UNIT PRICE", "LINE TOTAL"]]
    for index, item in enumerate(order.items, start=1):
        item_rows.append(
            [
                str(index),
                item.sku,
                Paragraph(item.description, styles["Small"]),
                amount(item.quantity),
                amount(item.unit_price),
                amount(item.total),
            ]
        )
    items = Table(
        item_rows, colWidths=[13 * mm, 31 * mm, 65 * mm, 15 * mm, 25 * mm, 28 * mm], repeatRows=1
    )
    items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), accent),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, 0), 7.2),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.45, border),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, wash]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    subtotal = sum((item.total for item in order.items), Decimal("0"))
    tax = Decimal("0")
    total = subtotal + tax
    totals = Table(
        [
            ["Subtotal", amount(subtotal)],
            ["Tax", amount(tax)],
            [Paragraph(f"<b>ORDER TOTAL ({order.currency})</b>", styles["Right"]), amount(total)],
        ],
        colWidths=[48 * mm, 30 * mm],
        hAlign="RIGHT",
    )
    totals.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LINEABOVE", (0, -1), (-1, -1), 1.1, accent),
                ("BACKGROUND", (0, -1), (-1, -1), wash),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    notes = Table(
        [
            [Paragraph("DELIVERY NOTES", styles["Section"])],
            [Paragraph(order.notes, styles["Small"])],
        ],
        colWidths=[177 * mm],
    )
    notes.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.55, border),
                ("BACKGROUND", (0, 0), (-1, 0), wash),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    footer = Table(
        [
            [
                Paragraph(f"Authorized buyer: <b>{order.buyer}</b>", styles["Muted"]),
                Paragraph(order.buyer_email, styles["Right"]),
            ]
        ],
        colWidths=[108 * mm, 69 * mm],
    )
    footer.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 0.6, border),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story = [
        header,
        Spacer(1, 3 * mm),
        HRFlowable(color=accent, thickness=2),
        Spacer(1, 5 * mm),
        meta,
        Spacer(1, 6 * mm),
        address,
        Spacer(1, 7 * mm),
        Paragraph("ORDER ITEMS", styles["Section"]),
        items,
        Spacer(1, 5 * mm),
        totals,
        Spacer(1, 7 * mm),
        notes,
        Spacer(1, 9 * mm),
        footer,
    ]
    doc.build(story)
    return output


def main() -> None:
    for order in ORDERS:
        print(build_order(order).resolve())


if __name__ == "__main__":
    main()
