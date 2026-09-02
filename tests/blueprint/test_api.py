"""Blueprint validation HTTP API tests."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_validate_blueprint_api_returns_summary(
    client: TestClient,
    example_blueprint_path: Path,
) -> None:
    response = client.post(
        "/api/v1/blueprints/validate",
        json={
            "content": example_blueprint_path.read_text(encoding="utf-8"),
            "format": "yaml",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["errors"] == []
    assert body["blueprint"] == {
        "name": "customer-refund-assistant",
        "version": "0.1.0",
        "knowledge_sources": 2,
        "tools": 3,
        "agents": 4,
        "rag_strategy": "agentic",
        "orchestration_pattern": "supervisor",
    }


def test_validate_blueprint_api_returns_parse_error(client: TestClient) -> None:
    response = client.post(
        "/api/v1/blueprints/validate",
        json={"content": "kind: [", "format": "yaml"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body["blueprint"] is None
    assert body["errors"][0]["code"] == "parse_error"


def test_validate_blueprint_api_rejects_unknown_format(client: TestClient) -> None:
    response = client.post(
        "/api/v1/blueprints/validate",
        json={"content": "{}", "format": "toml"},
    )

    assert response.status_code == 422
