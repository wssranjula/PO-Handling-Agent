from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.config import Settings, get_settings
from app.db import SessionFactory
from app.services.extraction import Extractor, build_extractor
from app.services.rag import RAGService
from app.workflows.nodes import PurchaseOrderNodes
from app.workflows.state import POState


def build_workflow(
    extractor: Extractor | None = None,
    settings: Settings | None = None,
    rag_service: RAGService | None = None,
    enable_rag: bool = True,
):
    settings = settings or get_settings()
    nodes = PurchaseOrderNodes(
        settings=settings,
        extractor=extractor or build_extractor(settings),
        rag_service=rag_service or RAGService(settings),
        session_factory=SessionFactory,
        enable_rag=enable_rag,
    )
    graph = StateGraph(POState)
    graph.add_node("parse_document", nodes.parse_document)
    graph.add_node("extract_order", nodes.extract_order)
    graph.add_node("enrich_order", nodes.enrich_order)
    graph.add_node("validate_order", nodes.validate_order)
    graph.add_node("complete_auto_process", nodes.complete_auto_process)
    graph.add_node("request_review", nodes.request_review)
    graph.add_edge(START, "parse_document")
    graph.add_edge("parse_document", "extract_order")
    graph.add_edge("extract_order", "enrich_order")
    graph.add_edge("enrich_order", "validate_order")
    graph.add_conditional_edges(
        "validate_order",
        nodes.select_route,
        {
            "auto_process": "complete_auto_process",
            "human_review": "request_review",
        },
    )
    graph.add_edge("complete_auto_process", END)
    graph.add_edge("request_review", END)
    return graph.compile()


@lru_cache(maxsize=1)
def get_workflow():
    return build_workflow()
