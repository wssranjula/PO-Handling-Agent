import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT_DIR = Path("output/pdf")
TMP_DIR = Path("tmp/pdfs")


def styles():
    sheet = getSampleStyleSheet()
    sheet.add(
        ParagraphStyle(
            name="DemoTitle",
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=23,
            textColor=colors.HexColor("#17241D"),
        )
    )
    sheet.add(
        ParagraphStyle(
            name="DemoSmall",
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#5F6A64"),
        )
    )
    sheet.add(
        ParagraphStyle(
            name="DemoBody",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1D2822"),
        )
    )
    sheet.add(
        ParagraphStyle(
            name="DemoLabel",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#68736D"),
        )
    )
    sheet.add(
        ParagraphStyle(
            name="DemoSection",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#245F47"),
        )
    )
    return sheet


def create_rag_enrichment_po() -> Path:
    output = OUTPUT_DIR / "loom-01-rag-enrichment-messy.pdf"
    sheet = styles()
    green = colors.HexColor("#245F47")
    pale = colors.HexColor("#EEF3F0")
    line = colors.HexColor("#CBD4CF")
    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Purchase Order NS-MEMO-826-14",
    )

    header = Table(
        [
            [
                Paragraph("NORTHSTAR STORES", sheet["DemoTitle"]),
                Paragraph(
                    "<para align='right'><b>P.O. / BUYER MEMO</b><br/>"
                    "Please use this sheet as our order</para>",
                    sheet["DemoBody"],
                ),
            ]
        ],
        colWidths=[92 * mm, 83 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, -1), 2, green),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    scribbled_meta = Table(
        [
            [
                Paragraph("OUR REF", sheet["DemoLabel"]),
                Paragraph("NS / MEMO / 826-14", sheet["DemoBody"]),
                Paragraph("written", sheet["DemoLabel"]),
                Paragraph("14 Aug 2026", sheet["DemoBody"]),
            ],
            [
                Paragraph("account name", sheet["DemoLabel"]),
                Paragraph("Northstar Stores", sheet["DemoBody"]),
                Paragraph("money", sheet["DemoLabel"]),
                Paragraph("All amounts US dollars", sheet["DemoBody"]),
            ],
            [
                Paragraph("terms agreed", sheet["DemoLabel"]),
                Paragraph("45 days net", sheet["DemoBody"]),
                Paragraph("need by", sheet["DemoLabel"]),
                Paragraph("before month end - 29 Aug 2026", sheet["DemoBody"]),
            ],
        ],
        colWidths=[27 * mm, 55 * mm, 27 * mm, 66 * mm],
    )
    scribbled_meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), pale),
                ("GRID", (0, 0), (-1, -1), 0.5, line),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    ship_to = Table(
        [
            [
                Paragraph(
                    "<b>Deliver exactly here (not billing):</b><br/>"
                    "Northstar Home Stores - Central Warehouse<br/>"
                    "Warehouse 4, 18 Harbour Road<br/>Colombo 01, Sri Lanka<br/>"
                    "Attention: Receiving Desk",
                    sheet["DemoBody"],
                ),
                Paragraph(
                    "Supplier:<br/><b>Example Distribution Co.</b><br/>"
                    "142 Galle Road, Colombo 03<br/>sales@example-distribution.test",
                    sheet["DemoBody"],
                ),
            ]
        ],
        colWidths=[96 * mm, 79 * mm],
    )
    ship_to.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, line),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, line),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    items = Table(
        [
            ["Ln", "What our buyer calls it", "Pack / quantity", "Each", "Extension"],
            [
                "01",
                Paragraph(
                    "blue thermal bottle<br/>"
                    "<font size='8'>insulated drink bottle, blue, 16 oz</font>",
                    sheet["DemoBody"],
                ),
                "12 units",
                "$18.50",
                "$222.00",
            ],
            [
                "02",
                Paragraph(
                    "replacement bottle lid<br/><font size='8'>spares for the 16 oz bottles</font>",
                    sheet["DemoBody"],
                ),
                "25 ea",
                "$2.00",
                "$50.00",
            ],
        ],
        colWidths=[12 * mm, 78 * mm, 31 * mm, 26 * mm, 28 * mm],
    )
    items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), green),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, line),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    totals = Table(
        [
            ["Merchandise", "$272.00"],
            ["Tax - exempt", "$0.00"],
            [Paragraph("<b>TOTAL TO PAY</b>", sheet["DemoBody"]), "$272.00 USD"],
        ],
        colWidths=[45 * mm, 34 * mm],
        hAlign="RIGHT",
    )
    totals.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 1.2, green),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story = [
        header,
        Spacer(1, 5 * mm),
        scribbled_meta,
        Spacer(1, 6 * mm),
        ship_to,
        Spacer(1, 7 * mm),
        Paragraph("ITEM NOTES / ORDER LINES", sheet["DemoSection"]),
        items,
        Spacer(1, 5 * mm),
        totals,
        Spacer(1, 8 * mm),
        KeepTogether(
            [
                Paragraph("HANDWRITTEN-STYLE NOTES TYPED UP", sheet["DemoSection"]),
                Paragraph(
                    "Use our wording above. Quote NS/MEMO/826-14 on cartons. "
                    "No split delivery. Buyer: Maya P. / Procurement.",
                    sheet["DemoBody"],
                ),
            ]
        ),
    ]
    doc.build(story)
    return output


def create_ambiguous_missing_po() -> Path:
    output = OUTPUT_DIR / "loom-02-ambiguous-missing-fields.pdf"
    sheet = styles()
    amber = colors.HexColor("#9A571B")
    line = colors.HexColor("#D8D0C7")
    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=19 * mm,
        rightMargin=19 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Draft Purchase Order - incomplete",
    )

    meta = Table(
        [
            [Paragraph("PURCHASE ORDER - DRAFT", sheet["DemoTitle"]), ""],
            [Paragraph("Customer supplied reference", sheet["DemoLabel"]), "Q-778 / maybe PO-?"],
            [Paragraph("Ordering organization", sheet["DemoLabel"]), "North Star Retail Group"],
            [Paragraph("Date sent", sheet["DemoLabel"]), "Friday afternoon"],
            [Paragraph("Currency", sheet["DemoLabel"]), "not written - buyer to confirm"],
            [Paragraph("Payment", sheet["DemoLabel"]), "same as last time"],
        ],
        colWidths=[72 * mm, 101 * mm],
    )
    meta.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (1, 0)),
                ("LINEBELOW", (0, 0), (-1, 0), 2, amber),
                ("GRID", (0, 1), (-1, -1), 0.55, line),
                ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#F5EFE9")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    delivery = Table(
        [
            [Paragraph("DELIVERY", sheet["DemoSection"])],
            [
                Paragraph(
                    "Send to the usual main warehouse. The old note says Harbour Road, "
                    "but the buyer also mentioned Kandy on the phone. Call before dispatch.",
                    sheet["DemoBody"],
                )
            ],
        ],
        colWidths=[173 * mm],
    )
    delivery.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, line),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5EFE9")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    items = Table(
        [
            ["Description from email", "Qty", "Price", "Amount"],
            [
                Paragraph(
                    "white mugs - boxed ones<br/><font size='8'>No SKU was included</font>",
                    sheet["DemoBody"],
                ),
                "ten?",
                "7.50",
                "75.00",
            ],
            [
                Paragraph(
                    "blue bottles, medium size<br/><font size='8'>Buyer wrote: maybe 16 oz</font>",
                    sheet["DemoBody"],
                ),
                "12",
                "blank",
                "not calculated",
            ],
        ],
        colWidths=[88 * mm, 22 * mm, 28 * mm, 35 * mm],
    )
    items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), amber),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.55, line),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story = [
        meta,
        Spacer(1, 8 * mm),
        delivery,
        Spacer(1, 8 * mm),
        Paragraph("REQUESTED ITEMS", sheet["DemoSection"]),
        items,
        Spacer(1, 8 * mm),
        Paragraph(
            "Document total: approximately 75 plus the bottles. Tax status is not stated. "
            "Do not ship until purchasing confirms the missing details.",
            sheet["DemoBody"],
        ),
        Spacer(1, 12 * mm),
        Paragraph(
            "Prepared from an incomplete email thread - no authorized signature supplied.",
            sheet["DemoSmall"],
        ),
    ]
    doc.build(story)
    return output


def load_scan_font(size: int, bold: bool = False):
    candidate = Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf")
    if candidate.exists():
        return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def create_image_only_scan_po() -> Path:
    output = OUTPUT_DIR / "loom-03-image-only-bad-scan.pdf"
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    image_path = TMP_DIR / "loom-bad-scan.jpg"
    random.seed(82614)
    width, height = 1240, 1754
    page = Image.new("L", (width, height), 238)
    draw = ImageDraw.Draw(page)
    title = load_scan_font(44, bold=True)
    heading = load_scan_font(24, bold=True)
    body = load_scan_font(22)
    small = load_scan_font(18)

    draw.rectangle((75, 70, 1165, 1680), fill=246, outline=135, width=2)
    draw.text((105, 100), "ACME RETAIL LTD", font=title, fill=36)
    draw.text((760, 108), "PURCHASE ORDER", font=heading, fill=42)
    draw.line((105, 170, 1135, 170), fill=80, width=3)
    draw.text((105, 210), "PO: ACM-SCAN-992", font=heading, fill=48)
    draw.text((760, 215), "Date: 14/08/26", font=body, fill=55)
    draw.text((105, 270), "Terms: NET 30   Currency: USD", font=body, fill=50)
    draw.text((105, 340), "SHIP TO", font=heading, fill=42)
    address = [
        "Acme Retail - Kandy Receiving",
        "Dock 2, 55 Lake Avenue",
        "Kandy, Sri Lanka",
        "Attention: Stores Team",
    ]
    for index, line in enumerate(address):
        draw.text((105, 385 + index * 32), line, font=body, fill=52)

    top = 560
    columns = [105, 220, 500, 780, 930, 1135]
    for x in columns:
        draw.line((x, top, x, top + 230), fill=120, width=2)
    for y in [top, top + 55, top + 145, top + 230]:
        draw.line((105, y, 1135, y), fill=120, width=2)
    headers = ["LINE", "ITEM", "DESCRIPTION", "QTY", "PRICE"]
    for x, label in zip(columns[:-1], headers, strict=True):
        draw.text((x + 10, top + 14), label, font=small, fill=35)
    draw.text((118, top + 85), "1", font=body, fill=45)
    draw.text((230, top + 85), "MUG-WHT", font=body, fill=45)
    draw.text((510, top + 75), "White ceramic mug,", font=body, fill=45)
    draw.text((510, top + 105), "retail boxed", font=body, fill=45)
    draw.text((800, top + 85), "8", font=body, fill=45)
    draw.text((945, top + 85), "7.50", font=body, fill=45)

    draw.text((755, 850), "Subtotal", font=body, fill=45)
    draw.text((1010, 850), "60.00", font=body, fill=45)
    draw.text((755, 900), "Tax", font=body, fill=45)
    draw.text((1010, 900), "0.00", font=body, fill=45)
    draw.line((755, 945, 1135, 945), fill=90, width=2)
    draw.text((755, 970), "TOTAL USD", font=heading, fill=35)
    draw.text((1010, 970), "60.00", font=heading, fill=35)
    draw.text((105, 1120), "Notes: delivery before 5 September.", font=body, fill=55)
    draw.text((105, 1180), "Buyer: Nadeesha Silva", font=body, fill=55)
    draw.text((105, 1580), "SCANNED COPY - image only", font=small, fill=115)

    pixels = page.load()
    for _ in range(9500):
        x = random.randrange(width)
        y = random.randrange(height)
        pixels[x, y] = random.choice((180, 205, 225, 250))
    page = page.rotate(0.7, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=224)
    page = ImageEnhance.Contrast(page).enhance(0.82)
    page.save(image_path, "JPEG", quality=72)

    pdf = canvas.Canvas(str(output), pagesize=A4)
    pdf.setTitle("Image-only scanned purchase order ACM-SCAN-992")
    pdf.drawImage(str(image_path), 0, 0, width=A4[0], height=A4[1])
    pdf.showPage()
    pdf.save()
    return output


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in (
        create_rag_enrichment_po(),
        create_ambiguous_missing_po(),
        create_image_only_scan_po(),
    ):
        print(path.resolve())


if __name__ == "__main__":
    main()
