from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Route(StrEnum):
    AUTO_PROCESS = "auto_process"
    HUMAN_REVIEW = "human_review"


class LineItem(BaseModel):
    line_number: int = Field(ge=1)
    raw_description: str | None = Field(default=None, min_length=1)
    raw_sku: str | None = None
    resolved_sku: str | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    line_total: Decimal | None = Field(default=None, ge=0)


class PurchaseOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    po_number: str | None = None
    issue_date: date | None = None
    currency: str | None = None
    customer_name: str | None = None
    resolved_customer_id: str | None = None
    shipping_address: str | None = None
    requested_delivery_date: date | None = None
    payment_terms: str | None = None
    subtotal: Decimal | None = Field(default=None, ge=0)
    tax: Decimal | None = Field(default=None, ge=0)
    total: Decimal | None = Field(default=None, ge=0)
    line_items: list[LineItem] = Field(default_factory=list)


class SourceEvidence(BaseModel):
    """A verbatim document excerpt supporting one or more extracted fields."""

    field_paths: list[str] = Field(min_length=1)
    quoted_text: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)
    confidence: float = Field(ge=0, le=1)
    notes: str | None = None


class ExtractionWarning(BaseModel):
    code: str
    message: str
    field_path: str | None = None


class PurchaseOrderExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_is_purchase_order: bool
    order: PurchaseOrder
    evidence: list[SourceEvidence]
    warnings: list[ExtractionWarning]
    overall_confidence: float = Field(ge=0, le=1)


class ValidationResult(BaseModel):
    code: str
    passed: bool
    message: str
    severity: str = "error"


class RAGMatch(BaseModel):
    query: str
    entity_type: str
    entity_id: str | None = None
    entity_name: str | None = None
    similarity: float = Field(ge=-1, le=1)
    chunk_id: str
    source_title: str
    content: str


class EnrichmentResult(BaseModel):
    order: PurchaseOrder
    matches: list[RAGMatch]


class IntakeResponse(BaseModel):
    message_id: str
    attachment_id: str
    run_id: str
    status: str


class ReviewDecision(BaseModel):
    corrected_order: PurchaseOrder
    reviewer: str = Field(min_length=1)
    notes: str | None = None


class ReviewRejection(BaseModel):
    reviewer: str = Field(min_length=1)
    reason: str = Field(min_length=1)
