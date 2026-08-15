from app.api import app


def test_required_routes_remain_in_openapi_contract() -> None:
    paths = app.openapi()["paths"]
    assert {
        "/health",
        "/integrations/gmail/status",
        "/integrations/gmail/poll",
        "/webhooks/email",
        "/runs/{run_id}",
        "/orders",
        "/orders/{order_id}",
        "/reviews",
        "/reviews/{review_id}",
        "/reviews/{review_id}/approve",
        "/reviews/{review_id}/reject",
    } <= set(paths)
