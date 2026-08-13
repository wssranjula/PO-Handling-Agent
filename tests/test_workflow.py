from pathlib import Path

import pytest

from app.services.extraction import DevelopmentExtractor
from app.workflow import build_workflow


@pytest.mark.asyncio
async def test_clean_order_routes_to_auto_process(tmp_path: Path) -> None:
    document = tmp_path / "po.txt"
    document.write_text(
        """PO Number: PO-10482
Issue Date: 2026-08-10
Currency: USD
Customer: Acme Retail
Shipping Address: 10 Main Street
Subtotal: 4850.00
Tax: 0
Total: 4850.00
item|BTL-BLU-16|Blue insulated bottle 16oz|100|48.50
""",
        encoding="utf-8",
    )
    result = await build_workflow(extractor=DevelopmentExtractor(), enable_rag=False).ainvoke(
        {"attachment_path": str(document), "content_type": "text/plain", "run_id": "test"}
    )
    assert result["route"] == "auto_process"
    assert result["review_reasons"] == []


@pytest.mark.asyncio
async def test_incomplete_order_routes_to_review(tmp_path: Path) -> None:
    document = tmp_path / "po.txt"
    document.write_text("PO Number: PO-1\nCustomer: Acme", encoding="utf-8")
    result = await build_workflow(extractor=DevelopmentExtractor(), enable_rag=False).ainvoke(
        {"attachment_path": str(document), "content_type": "text/plain", "run_id": "test"}
    )
    assert result["route"] == "human_review"
    assert "REQUIRED_CURRENCY" in result["review_reasons"]
