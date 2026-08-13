from types import SimpleNamespace

import pytest

from app.config import Settings
from app.schemas import PurchaseOrderExtraction
from app.services.extraction import OpenAIExtractor


class FakeResponses:
    def __init__(self, parsed: PurchaseOrderExtraction) -> None:
        self.parsed = parsed
        self.kwargs: dict = {}

    async def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.parsed)


@pytest.mark.asyncio
async def test_openai_extractor_uses_pydantic_structured_output() -> None:
    parsed = PurchaseOrderExtraction.model_validate(
        {
            "document_is_purchase_order": True,
            "order": {
                "po_number": "PO-42",
                "currency": "USD",
                "customer_name": "Acme",
                "shipping_address": "10 Main Street",
                "total": "10.00",
                "line_items": [],
            },
            "evidence": [
                {
                    "field_paths": ["order.po_number"],
                    "quoted_text": "PO-42",
                    "confidence": 0.99,
                }
            ],
            "warnings": [],
            "overall_confidence": 0.95,
        }
    )
    responses = FakeResponses(parsed)
    client = SimpleNamespace(responses=responses)
    extractor = OpenAIExtractor(Settings(openai_api_key="test-key"), client=client)

    result = await extractor.extract("Purchase order PO-42")

    assert result.order.po_number == "PO-42"
    assert responses.kwargs["text_format"] is PurchaseOrderExtraction
    assert "untrusted data" in responses.kwargs["input"][0]["content"]


@pytest.mark.asyncio
async def test_openai_extractor_rejects_oversized_document() -> None:
    extractor = OpenAIExtractor(
        Settings(openai_api_key="test-key", max_document_characters=5),
        client=SimpleNamespace(),
    )
    with pytest.raises(RuntimeError, match="exceeds"):
        await extractor.extract("too long")
