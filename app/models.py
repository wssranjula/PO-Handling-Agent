import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_id() -> str:
    return str(uuid.uuid4())


class ProcessingStatus(StrEnum):
    RECEIVED = "received"
    PARSED = "parsed"
    EXTRACTED = "extracted"
    VALIDATED = "validated"
    AUTO_PROCESSED = "auto_processed"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    FAILED = "failed"


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    provider_message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    sender: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(998), default="")
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    attachments: Mapped[list["Attachment"]] = relationship(back_populates="email")


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        UniqueConstraint("email_id", "sha256", name="uq_email_attachment_hash"),
        UniqueConstraint(
            "email_id",
            "provider_attachment_id",
            name="uq_email_provider_attachment",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email_id: Mapped[str] = mapped_column(ForeignKey("email_messages.id"), index=True)
    provider_attachment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_path: Mapped[str] = mapped_column(Text)

    email: Mapped[EmailMessage] = relationship(back_populates="attachments")
    run: Mapped["ProcessingRun | None"] = relationship(back_populates="attachment")


class ProcessingRun(Base):
    __tablename__ = "processing_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    attachment_id: Mapped[str] = mapped_column(
        ForeignKey("attachments.id"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default=ProcessingStatus.RECEIVED)
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    validation_results: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    review_reasons: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    attachment: Mapped[Attachment] = relationship(back_populates="run")
    review_case: Mapped["ReviewCase | None"] = relationship(back_populates="run")
    enrichment: Mapped["RunEnrichment | None"] = relationship(back_populates="run")
    draft_order: Mapped["DraftOrder | None"] = relationship(back_populates="run")


class ReviewCase(Base):
    __tablename__ = "review_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("processing_runs.id"), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    reasons: Mapped[list[str]] = mapped_column(JSON)
    resolution: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[ProcessingRun] = relationship(back_populates="review_case")


class RunEnrichment(Base):
    __tablename__ = "run_enrichments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("processing_runs.id"), unique=True, index=True)
    resolved_order: Mapped[dict[str, Any]] = mapped_column(JSON)
    matches: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[ProcessingRun] = relationship(back_populates="enrichment")


class DraftOrder(Base):
    __tablename__ = "draft_orders"
    __table_args__ = (
        UniqueConstraint("customer_id", "po_number", name="uq_draft_customer_po_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("processing_runs.id"), unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    po_number: Mapped[str] = mapped_column(String(255), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    order_data: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[ProcessingRun] = relationship(back_populates="draft_order")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_shipping_addresses: Mapped[list[str]] = mapped_column(JSON, default=list)
    payment_terms: Mapped[str | None] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    standard_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CustomerProductPrice(Base):
    __tablename__ = "customer_product_prices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"), index=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("customer_id", "sku", "currency", name="uq_customer_sku_currency"),
    )


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(String(50), index=True)
    source_path: Mapped[str] = mapped_column(Text)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="document")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")
