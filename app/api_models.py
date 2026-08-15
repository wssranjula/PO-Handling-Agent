from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.schemas import PurchaseOrder, ValidationResult


class HealthResponse(BaseModel):
    status: str


class GmailStatusResponse(BaseModel):
    enabled: bool
    authorized: bool
    credentials_configured: bool
    poll_interval_seconds: int
    query: str


class GmailPollResponse(BaseModel):
    messages: int
    attachments: int
    ingested: int
    failed: int
    duplicates: int
    skipped: int


class EnrichmentResponse(BaseModel):
    resolved_order: PurchaseOrder
    matches: list[dict[str, Any]]


class RunDraftResponse(BaseModel):
    id: str
    status: str
    order_data: PurchaseOrder


class RunResponse(BaseModel):
    id: str
    status: str
    extracted_data: dict[str, Any] | None
    validation_results: list[ValidationResult] | None
    review_reasons: list[str] | None
    enrichment: EnrichmentResponse | None
    draft_order: RunDraftResponse | None
    error: dict[str, Any] | None


class OrderResponse(BaseModel):
    id: str
    run_id: str
    customer_id: str
    customer_name: str | None
    po_number: str
    currency: str
    total: Decimal
    status: str
    order_data: PurchaseOrder
    created_at: datetime


class ReviewSummaryResponse(BaseModel):
    id: str
    run_id: str
    status: str
    reasons: list[str]
    resolution: dict[str, Any] | None
    created_at: datetime


class ReviewDetailResponse(ReviewSummaryResponse):
    extracted_data: dict[str, Any] | None
    validation_results: list[ValidationResult] | None
    error: dict[str, Any] | None
    enrichment: EnrichmentResponse | None


class ReviewActionResponse(BaseModel):
    status: str
    review_reasons: list[str] | None = None
    draft_order_id: str | None = None
    review_id: str | None = None
    run_id: str | None = None
