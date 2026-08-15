from typing import Any, TypedDict


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
    error: dict[str, Any]
