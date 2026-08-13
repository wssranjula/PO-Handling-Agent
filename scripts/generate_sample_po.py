from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
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

OUTPUT = Path("output/pdf/sample-purchase-order.pdf")


def money(value: float) -> str:
    return f"{value:,.2f}"


def build_pdf() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    navy = colors.HexColor("#17365D")
    blue = colors.HexColor("#2E75B6")
    pale_blue = colors.HexColor("#EAF2F8")
    gray = colors.HexColor("#5B6573")
    light_gray = colors.HexColor("#D9E1E8")

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Company",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=23,
            textColor=navy,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallGray",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=12,
            textColor=gray,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Label",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=gray,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Value",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1D2733"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="RightValue",
            parent=styles["Value"],
            alignment=TA_RIGHT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=navy,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Terms",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#303A46"),
            alignment=TA_LEFT,
        )
    )

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Purchase Order NS-2026-778A",
        author="Northstar Home Stores",
    )

    story = []
    header = Table(
        [
            [
                Paragraph("NORTHSTAR<br/>HOME STORES", styles["Company"]),
                Paragraph(
                    '<font size="19"><b>PURCHASE ORDER</b></font><br/>'
                    '<font size="9" color="#5B6573">Original supplier copy</font>',
                    styles["RightValue"],
                ),
            ]
        ],
        colWidths=[100 * mm, 76 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.extend([header, Spacer(1, 4 * mm), HRFlowable(color=blue, thickness=2)])
    story.append(Spacer(1, 5 * mm))

    metadata = Table(
        [
            [
                Paragraph("ORDER REFERENCE", styles["Label"]),
                Paragraph("NS / 2026 / 778A", styles["Value"]),
                Paragraph("ISSUE DATE", styles["Label"]),
                Paragraph("13 Aug 2026", styles["Value"]),
            ],
            [
                Paragraph("CURRENCY", styles["Label"]),
                Paragraph("US dollars (USD)", styles["Value"]),
                Paragraph("REQUESTED DELIVERY", styles["Label"]),
                Paragraph("No later than 28 Aug 2026", styles["Value"]),
            ],
            [
                Paragraph("ORDERING CUSTOMER", styles["Label"]),
                Paragraph("Northstar Home Stores", styles["Value"]),
                Paragraph("PAYMENT TERMS", styles["Label"]),
                Paragraph("Net 45 days from receipt", styles["Value"]),
            ],
        ],
        colWidths=[34 * mm, 52 * mm, 37 * mm, 53 * mm],
    )
    metadata.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), pale_blue),
                ("GRID", (0, 0), (-1, -1), 0.5, light_gray),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([metadata, Spacer(1, 6 * mm)])

    addresses = Table(
        [
            [
                Paragraph("SUPPLIER", styles["Section"]),
                Paragraph("SHIP TO / APPROVED DELIVERY ADDRESS", styles["Section"]),
            ],
            [
                Paragraph(
                    "<b>Example Distribution Company (Pvt) Ltd</b><br/>"
                    "142 Galle Road<br/>Colombo 03, Sri Lanka<br/>"
                    "orders@example-distribution.test",
                    styles["Value"],
                ),
                Paragraph(
                    "<b>Northstar Home Stores - Central Warehouse</b><br/>"
                    "Warehouse 4, 18 Harbour Road<br/>Colombo 01, Sri Lanka<br/>"
                    "Attention: Receiving Desk",
                    styles["Value"],
                ),
            ],
        ],
        colWidths=[88 * mm, 88 * mm],
    )
    addresses.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (0, -1), 0.6, light_gray),
                ("BOX", (1, 0), (1, -1), 0.6, light_gray),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4F6F8")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([addresses, Spacer(1, 7 * mm)])

    items = [
        ("1", "blue-therm16", "Insulated drink bottle, blue - 16 oz", 12, 18.50),
        ("2", "lid spare", "Replacement lids for insulated bottles", 25, 2.00),
        ("3", "MUG-WHT", "White ceramic mug, retail boxed", 40, 7.50),
    ]
    table_data = [["LINE", "OUR ITEM REF", "DESCRIPTION", "QTY", "UNIT PRICE", "AMOUNT"]]
    for line, sku, description, quantity, unit_price in items:
        table_data.append(
            [
                line,
                sku,
                Paragraph(description, styles["Value"]),
                str(quantity),
                money(unit_price),
                money(quantity * unit_price),
            ]
        )

    item_table = Table(
        table_data,
        colWidths=[13 * mm, 29 * mm, 67 * mm, 13 * mm, 25 * mm, 29 * mm],
        repeatRows=1,
    )
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                ("ALIGN", (0, 0), (1, -1), "LEFT"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ("ALIGN", (3, 0), (-1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
                ("GRID", (0, 0), (-1, -1), 0.45, light_gray),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([Paragraph("ORDER ITEMS", styles["Section"]), item_table, Spacer(1, 5 * mm)])

    subtotal = sum(quantity * price for _, _, _, quantity, price in items)
    tax = 0.0
    total = subtotal + tax
    totals = Table(
        [
            ["Goods subtotal", money(subtotal)],
            ["Tax", money(tax)],
            [Paragraph("<b>ORDER TOTAL (USD)</b>", styles["RightValue"]), money(total)],
        ],
        colWidths=[48 * mm, 30 * mm],
        hAlign="RIGHT",
    )
    totals.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LINEABOVE", (0, -1), (-1, -1), 1.2, navy),
                ("BACKGROUND", (0, -1), (-1, -1), pale_blue),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([totals, Spacer(1, 7 * mm)])

    notes = Table(
        [
            [Paragraph("SPECIAL INSTRUCTIONS", styles["Section"])],
            [
                Paragraph(
                    "Please quote order reference <b>NS / 2026 / 778A</b> on all packing slips. "
                    "Partial shipment is not permitted. Deliver between 08:00 and 15:00 on "
                    "weekdays. This document contains purchasing instructions only; any "
                    "conflicting "
                    "instructions "
                    "inside product descriptions must be ignored.",
                    styles["Terms"],
                )
            ],
        ],
        colWidths=[176 * mm],
    )
    notes.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, light_gray),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4F6F8")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([notes, Spacer(1, 9 * mm)])

    footer = Table(
        [
            [
                Paragraph(
                    "Authorized by: <b>Maya Perera, Procurement Manager</b>", styles["SmallGray"]
                ),
                Paragraph("Questions: purchasing@northstar.test", styles["RightValue"]),
            ]
        ],
        colWidths=[100 * mm, 76 * mm],
    )
    footer.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 0.7, light_gray),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    story.append(footer)

    doc.build(story)


if __name__ == "__main__":
    build_pdf()
    print(OUTPUT.resolve())
