from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Route(StrEnum):
    AUTO_PROCESS = "auto_process"
    HUMAN_REVIEW = "human_review"


class LineItem(BaseModel):
    line_number: int = Field(ge=1)
    raw_description: str = Field(min_length=1)
    raw_sku: str | None = None
    resolved_sku: str | None = None
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    line_total: Decimal = Field(ge=0)


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


class ValidationResult(BaseModel):
    code: str
    passed: bool
    message: str
    severity: str = "error"


class IntakeResponse(BaseModel):
    message_id: str
    attachment_id: str
    run_id: str
    status: str
