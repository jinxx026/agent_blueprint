from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from app.connectors import ConnectorRegistry, FunctionConnector, ManagedToolExecutor
from app.runtime import BlueprintExecutor
from app.runtime.model import AgentPrompt, AgentResponse, ToolRequest


class ApiRefundModel:
    def invoke(self, prompt: AgentPrompt) -> AgentResponse:
        if prompt.prior_reports:
            return AgentResponse(content="审批流程完成")
        if prompt.agent.id == "refund-specialist":
            return AgentResponse(
                content="创建退款草稿",
                tool_requests=(
                    ToolRequest(
                        tool_id="create_refund_draft",
                        arguments={
                            "order_id": "O-API",
                            "amount": 100,
                            "reason": "customer request",
                        },
                    ),
                ),
            )
        return AgentResponse(content="completed")


def test_execute_endpoint_runs_compiled_langgraph(
    client: TestClient, example_blueprint_path: Path
) -> None:
    response = client.post(
        "/api/v1/blueprints/execute",
        json={
            "content": example_blueprint_path.read_text(encoding="utf-8"),
            "format": "yaml",
            "message": "普通商品签收三天，可以退款吗？",
            "thread_id": "api-runtime-test",
            "knowledge_documents": [
                {
                    "source_id": "after_sales_policy",
                    "content": "普通商品七天内可以申请退款。",
                    "citation": "policy:seven-days",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["executed"] is True
    assert body["errors"] == []
    assert body["result"]["thread_id"] == "api-runtime-test"
    assert body["result"]["citations"] == ["policy:seven-days"]
    assert len(body["result"]["reports"]) == 3


def test_execute_endpoint_can_use_contextual_rag_pipeline(
    client: TestClient,
    example_blueprint_path: Path,
    auth_headers: Callable[[str, tuple[str, ...]], dict[str, str]],
) -> None:
    response = client.post(
        "/api/v1/blueprints/execute",
        json={
            "content": example_blueprint_path.read_text(encoding="utf-8"),
            "format": "yaml",
            "message": "退款需要什么材料？",
            "tenant_id": "acme",
            "user_roles": ["customer_service"],
            "rag_documents": [
                {
                    "tenant_id": "acme",
                    "source_id": "after_sales_policy",
                    "document_id": "refund-policy",
                    "title": "退款政策",
                    "content": "# 申请材料\n退款需要订单号和购买凭证。其他说明与本问题无关。",
                    "allowed_roles": ["customer_service"],
                    "citation_base": "kb://acme/refund-policy",
                }
            ],
        },
        headers=auth_headers("acme", ("customer_service",)),
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert "订单号" in result["answer"]
    assert result["citations"][0].startswith("kb://acme/refund-policy#chunk=")


def test_approval_api_resumes_the_same_langgraph_checkpoint(
    client: TestClient, example_blueprint_path: Path
) -> None:
    calls: list[dict[str, object]] = []
    managed = ManagedToolExecutor(
        ConnectorRegistry(
            {
                "connector://commerce/refunds": FunctionConnector(
                    {
                        "create_refund_draft": lambda arguments: (
                            calls.append(arguments) or {"ok": True}
                        )
                    }
                )
            }
        )
    )
    client.app.state.blueprint_executor = BlueprintExecutor(model=ApiRefundModel(), tools=managed)
    started = client.post(
        "/api/v1/blueprints/execute",
        json={
            "content": example_blueprint_path.read_text(encoding="utf-8"),
            "format": "yaml",
            "message": "创建退款草稿",
            "thread_id": "api-approval",
            "user_roles": ["customer_service"],
            "policy_context": {"customer_identity_verified": True},
        },
    )
    pending = started.json()["result"]
    assert pending["status"] == "pending_approval"
    assert calls == []

    approval = pending["pending_approvals"][0]
    resumed = client.post(
        "/api/v1/executions/api-approval/resume",
        json={
            "approval_id": approval["approval_id"],
            "decision": "approve",
            "reason": "主管核对通过",
            "approver_roles": ["supervisor"],
        },
    )

    assert resumed.status_code == 200
    assert resumed.json()["status"] == "completed"
    assert len(calls) == 1
    assert managed.audit.records[0].status == "succeeded"
