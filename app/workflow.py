from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas import Route
from app.services.documents import extract_text
from app.services.extraction import DevelopmentExtractor
from app.services.validation import validate_purchase_order


class POState(TypedDict, total=False):
    run_id: str
    attachment_path: str
    content_type: str
    document_text: str
    extracted_order: dict[str, Any]
    validation_results: list[dict[str, Any]]
    review_reasons: list[str]
    route: str
    error: dict[str, Any]


def build_workflow(extractor: DevelopmentExtractor | None = None):
    extractor = extractor or DevelopmentExtractor()

    async def parse_document(state: POState) -> dict[str, Any]:
        text = extract_text(Path(state["attachment_path"]), state["content_type"])
        if not text.strip():
            raise ValueError("No readable text found in attachment")
        return {"document_text": text}
#need to use llm to do the extraction
    async def extract_order(state: POState) -> dict[str, Any]:
        order = await extractor.extract(state["document_text"])
        return {"extracted_order": order.model_dump(mode="json")}

    async def validate_order(state: POState) -> dict[str, Any]:
        from app.schemas import PurchaseOrder

        order = PurchaseOrder.model_validate(state["extracted_order"])
        results = validate_purchase_order(order)
        failed = [result.code for result in results if not result.passed]
        route = Route.HUMAN_REVIEW if failed else Route.AUTO_PROCESS
        return {
            "validation_results": [result.model_dump(mode="json") for result in results],
            "review_reasons": failed,
            "route": route.value,
        }

    def select_route(state: POState) -> str:
        return state["route"]

    async def create_draft(state: POState) -> dict[str, Any]:
        # The external order-system adapter will be added after the workflow is evaluated.
        return {"route": Route.AUTO_PROCESS.value}

    async def request_review(state: POState) -> dict[str, Any]:
        return {"route": Route.HUMAN_REVIEW.value}

    graph = StateGraph(POState)
    graph.add_node("parse_document", parse_document)
    graph.add_node("extract_order", extract_order)
    graph.add_node("validate_order", validate_order)
    graph.add_node("create_draft", create_draft)
    graph.add_node("request_review", request_review)
    graph.add_edge(START, "parse_document")
    graph.add_edge("parse_document", "extract_order")
    graph.add_edge("extract_order", "validate_order")
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
