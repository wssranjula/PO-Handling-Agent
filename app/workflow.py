import logging
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import Settings, get_settings
from app.db import SessionFactory
from app.models import DraftOrder
from app.schemas import EnrichmentResult, PurchaseOrderExtraction, Route
from app.services.documents import extract_text
from app.services.extraction import Extractor, build_extractor
from app.services.rag import RAGService
from app.services.validation import (
    validate_authoritative_data,
    validate_extraction_quality,
    validate_purchase_order,
)

logger = logging.getLogger(__name__)


class POState(TypedDict, total=False):
    run_id: str
    attachment_path: str
    content_type: str
    document_text: str
    extraction: dict[str, Any]
    extracted_order: dict[str, Any]
    enrichment: dict[str, Any]
    rag_matches: list[dict[str, Any]]
    validation_results: list[dict[str, Any]]
    review_reasons: list[str]
    route: str
    draft_order_id: str
    error: dict[str, Any]


def build_workflow(
    extractor: Extractor | None = None,
    settings: Settings | None = None,
    rag_service: RAGService | None = None,
    enable_rag: bool = True,
):
    settings = settings or get_settings()
    extractor = extractor or build_extractor(settings)
    rag_service = rag_service or RAGService(settings)

    async def parse_document(state: POState) -> dict[str, Any]:
        logger.info(
            "workflow_node_started node=parse_document run_id=%s content_type=%s",
            state["run_id"],
            state["content_type"],
        )
        text = extract_text(Path(state["attachment_path"]), state["content_type"])
        if not text.strip():
            raise ValueError("No readable text found in attachment")
        logger.info(
            "workflow_node_completed node=parse_document run_id=%s characters=%s",
            state["run_id"],
            len(text),
        )
        return {"document_text": text}

    async def extract_order(state: POState) -> dict[str, Any]:
        logger.info("workflow_node_started node=extract_order run_id=%s", state["run_id"])
        extraction = await extractor.extract(state["document_text"])
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

    async def enrich_order(state: POState) -> dict[str, Any]:
        from app.schemas import PurchaseOrder

        logger.info("workflow_node_started node=enrich_order run_id=%s", state["run_id"])
        order = PurchaseOrder.model_validate(state["extracted_order"])
        if enable_rag:
            async with SessionFactory() as session:
                enrichment = await rag_service.enrich(session, order)
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

    async def validate_order(state: POState) -> dict[str, Any]:
        from app.schemas import PurchaseOrder

        extraction = PurchaseOrderExtraction.model_validate(state["extraction"])
        order = PurchaseOrder.model_validate(state["extracted_order"])
        authoritative_results = []
        if enable_rag:
            async with SessionFactory() as session:
                authoritative_results = await validate_authoritative_data(
                    session, order, settings, state["run_id"]
                )
        results = [
            *validate_extraction_quality(extraction, settings.min_extraction_confidence),
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

    def select_route(state: POState) -> str:
        return state["route"]

    async def create_draft(state: POState) -> dict[str, Any]:
        from app.schemas import PurchaseOrder

        if not enable_rag:
            return {"route": Route.AUTO_PROCESS.value}
        order = PurchaseOrder.model_validate(state["extracted_order"])
        if not all(
            [order.resolved_customer_id, order.po_number, order.currency, order.total is not None]
        ):
            raise ValueError("Validated order is missing fields required to create a draft")
        async with SessionFactory() as session:
            draft = DraftOrder(
                run_id=state["run_id"],
                customer_id=order.resolved_customer_id,
                po_number=order.po_number,
                currency=order.currency,
                total=order.total,
                order_data=order.model_dump(mode="json"),
            )
            session.add(draft)
            await session.commit()
            draft_id = draft.id
        logger.info(
            "workflow_routed run_id=%s destination=create_draft draft_order_id=%s",
            state["run_id"],
            draft_id,
        )
        return {"route": Route.AUTO_PROCESS.value, "draft_order_id": draft_id}

    async def request_review(state: POState) -> dict[str, Any]:
        logger.info(
            "workflow_routed run_id=%s destination=human_review reasons=%s",
            state["run_id"],
            state.get("review_reasons", []),
        )
        return {"route": Route.HUMAN_REVIEW.value}

    graph = StateGraph(POState)
    graph.add_node("parse_document", parse_document)
    graph.add_node("extract_order", extract_order)
    graph.add_node("enrich_order", enrich_order)
    graph.add_node("validate_order", validate_order)
    graph.add_node("create_draft", create_draft)
    graph.add_node("request_review", request_review)
    graph.add_edge(START, "parse_document")
    graph.add_edge("parse_document", "extract_order")
    graph.add_edge("extract_order", "enrich_order")
    graph.add_edge("enrich_order", "validate_order")
    graph.add_conditional_edges(
        "validate_order",
        select_route,
        {
            Route.AUTO_PROCESS.value: "create_draft",
            Route.HUMAN_REVIEW.value: "request_review",
        },
    )
    graph.add_edge("create_draft", END)
    graph.add_edge("request_review", END)
    return graph.compile()


workflow = build_workflow()
