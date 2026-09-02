from pathlib import Path

from fastapi.testclient import TestClient


def test_release_check_endpoint_returns_gate_report(
    client: TestClient, example_blueprint_path: Path
) -> None:
    response = client.post(
        "/api/v1/blueprints/release-check",
        json={
            "content": example_blueprint_path.read_text(encoding="utf-8"),
            "format": "yaml",
            "knowledge_documents": [
                {
                    "source_id": "after_sales_policy",
                    "content": "普通商品签收七天内可以退款。",
                    "citation": "kb:after_sales_policy:seven-days",
                }
            ],
            "cases": [
                {
                    "id": "release-smoke",
                    "description": "带引用的基础回答可以通过门禁",
                    "input": {
                        "actor_role": "customer_service",
                        "message": "普通商品七天内可以退款吗？",
                    },
                    "expected": {
                        "outcome": "completed",
                        "must_cite": ["after_sales_policy"],
                        "approval_required": False,
                    },
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evaluated"] is True
    assert body["report"]["passed"] is True
    assert body["report"]["score"] == 1.0


def test_release_check_rejects_invalid_blueprint(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/blueprints/release-check",
        json={
            "content": "kind: AgentBlueprint",
            "format": "yaml",
            "cases": [
                {
                    "id": "not-run",
                    "description": "无效蓝图不会进入评测",
                    "input": {"actor_role": "customer_service", "message": "hello"},
                    "expected": {"outcome": "completed"},
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["evaluated"] is False
    assert response.json()["report"] is None
    assert response.json()["errors"]
