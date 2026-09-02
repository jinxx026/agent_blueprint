"""ExecutionPlan compilation HTTP API tests."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_compile_api_returns_portable_execution_plan(
    client: TestClient,
    example_blueprint_path: Path,
) -> None:
    response = client.post(
        "/api/v1/blueprints/compile",
        json={
            "content": example_blueprint_path.read_text(encoding="utf-8"),
            "format": "yaml",
        },
    )

    assert response.status_code == 200
    body = response.json()
    plan = body["plan"]
    assert body["compiled"] is True
    assert body["errors"] == []
    assert plan["schema_version"] == "executionplan.agentblueprint.dev/v0.1"
    assert plan["plan_id"].startswith("customer-refund-assistant:0.1.0:")
    assert len(plan["source"]["content_hash"]) == 64
    assert len(plan["agents"]) == 4
    assert len(plan["retrievers"]) == 2
    assert plan["graph"]["entry_node"] == "supervisor"


def test_compile_api_returns_validation_errors_before_compilation(client: TestClient) -> None:
    response = client.post(
        "/api/v1/blueprints/compile",
        json={"content": "kind: AgentBlueprint", "format": "yaml"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["compiled"] is False
    assert body["plan"] is None
    assert body["errors"]


def test_compile_api_returns_policy_compiler_diagnostic(
    client: TestClient,
    example_blueprint_path: Path,
) -> None:
    content = example_blueprint_path.read_text(encoding="utf-8").replace(
        "amount <= 5000",
        "amount in [100, 200]",
    )

    response = client.post(
        "/api/v1/blueprints/compile",
        json={"content": content, "format": "yaml"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["compiled"] is False
    assert body["errors"][0]["code"] == "unsupported_policy_condition"
