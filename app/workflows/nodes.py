import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.schemas import (
    EnrichmentResult,
    PurchaseOrder,
    PurchaseOrderExtraction,
    Route,
)
from app.services.documents import extract_text
from app.services.extraction import Extractor
from app.services.rag import RAGService
from app.services.validation import (
    validate_authoritative_data,
    validate_extraction_quality,
    validate_purchase_order,
)
from app.workflows.state import POState

logger = logging.getLogger(__name__)


@dataclass
class PurchaseOrderNodes:
    settings: Settings
    extractor: Extractor
    rag_service: RAGService
    session_factory: async_sessionmaker[AsyncSession]
    enable_rag: bool = True

    async def parse_document(self, state: POState) -> dict[str, Any]:
        logger.info(
            "workflow_node_started node=parse_document run_id=%s content_type=%s",
            state["run_id"],
            state["content_type"],
        )
        document_text = extract_text(Path(state["attachment_path"]), state["content_type"])
        if not document_text.strip():
            raise ValueError("No readable text found in attachment")
        logger.info(
            "workflow_node_completed node=parse_document run_id=%s characters=%s",
            state["run_id"],
            len(document_text),
        )
        return {"document_text": document_text}

    async def extract_order(self, state: POState) -> dict[str, Any]:
        logger.info("workflow_node_started node=extract_order run_id=%s", state["run_id"])
        extraction = await self.extractor.extract(state["document_text"])
        logger.info(
            "workflow_node_completed node=extract_order run_id=%s po_number=%s confidence=%.2f",
            state["run_id"],
            extraction.order.po_number,
            extraction.overall_confidence,
        )
        return {
            "extraction": extraction.model_dump(mode="json"),
            "extracted_order": extraction.order.model_dump(mode="json"),
        }

    async def enrich_order(self, state: POState) -> dict[str, Any]:
        logger.info("workflow_node_started node=enrich_order run_id=%s", state["run_id"])
        order = PurchaseOrder.model_validate(state["extracted_order"])
        if self.enable_rag:
            async with self.session_factory() as session:
                enrichment = await self.rag_service.enrich(session, order)
        else:
            enrichment = EnrichmentResult(order=order, matches=[])
        logger.info(
            "workflow_node_completed node=enrich_order run_id=%s customer_id=%s matches=%s",
            state["run_id"],
            enrichment.order.resolved_customer_id,
            len(enrichment.matches),
        )
        return {
            "enrichment": enrichment.model_dump(mode="json"),
            "extracted_order": enrichment.order.model_dump(mode="json"),
            "rag_matches": [match.model_dump(mode="json") for match in enrichment.matches],
        }

    async def validate_order(self, state: POState) -> dict[str, Any]:
        extraction = PurchaseOrderExtraction.model_validate(state["extraction"])
        order = PurchaseOrder.model_validate(state["extracted_order"])
        authoritative_results = []
        if self.enable_rag:
            async with self.session_factory() as session:
                authoritative_results = await validate_authoritative_data(
                    session, order, self.settings, state["run_id"]
                )
        results = [
            *validate_extraction_quality(extraction, self.settings.min_extraction_confidence),
            *validate_purchase_order(order),
            *authoritative_results,
        ]
        failed = [result.code for result in results if not result.passed]
        route = Route.HUMAN_REVIEW if failed else Route.AUTO_PROCESS
        logger.info(
            "workflow_validation_completed run_id=%s route=%s checks=%s failed=%s",
            state["run_id"],
            route.value,
            len(results),
            failed,
        )
        return {
            "validation_results": [result.model_dump(mode="json") for result in results],
            "review_reasons": failed,
            "route": route.value,
        }

    async def complete_auto_process(self, state: POState) -> dict[str, Any]:
        if self.enable_rag:
            order = PurchaseOrder.model_validate(state["extracted_order"])
            required = (
                order.resolved_customer_id,
                order.po_number,
                order.currency,
                order.total,
            )
            if any(value is None for value in required):
                raise ValueError("Validated order is missing fields required to create a draft")
        logger.info("workflow_routed run_id=%s destination=auto_process", state["run_id"])
        return {"route": Route.AUTO_PROCESS.value}

    async def request_review(self, state: POState) -> dict[str, Any]:
        logger.info(
            "workflow_routed run_id=%s destination=human_review reasons=%s",
            state["run_id"],
            state.get("review_reasons", []),
        )
        return {"route": Route.HUMAN_REVIEW.value}

    @staticmethod
    def select_route(state: POState) -> str:
        return state["route"]
