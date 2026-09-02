from pathlib import Path

import pytest

from app.blueprint.loader import BlueprintFormat
from app.blueprint.service import BlueprintService
from app.compiler import BlueprintCompiler
from app.connectors import ConnectorRegistry, FunctionConnector, ManagedToolExecutor
from app.governance import ApprovalDecision, ApprovalResume
from app.governance.approvals import ApprovalAuthorizationError
from app.runtime import BlueprintExecutor
from app.runtime.model import AgentPrompt, AgentResponse, ToolRequest


class RefundRequestModel:
    def invoke(self, prompt: AgentPrompt) -> AgentResponse:
        if prompt.prior_reports:
            return AgentResponse(
                content="主管已汇总：" + "；".join(r.content for r in prompt.prior_reports)
            )
        if prompt.agent.id == "refund-specialist":
            return AgentResponse(
                content="申请创建退款草稿",
                tool_requests=(
                    ToolRequest(
                        tool_id="create_refund_draft",
                        arguments={
                            "order_id": "O-1",
                            "amount": 100,
                            "reason": "customer request",
                        },
                    ),
                ),
            )
        return AgentResponse(content=f"{prompt.agent.id} completed")


def compile_plan(path: Path):
    result = BlueprintService().validate_text(
        path.read_text(encoding="utf-8"), BlueprintFormat.YAML
    )
    assert result.blueprint is not None
    return BlueprintCompiler().compile(result.blueprint)


def test_graph_pauses_before_side_effect_and_resumes_exactly_once(
    example_blueprint_path: Path,
) -> None:
    calls = 0

    def create_refund(arguments: dict[str, object]) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"draft_id": "D-1", **arguments}

    managed = ManagedToolExecutor(
        ConnectorRegistry(
            {
                "connector://commerce/refunds": FunctionConnector(
                    {"create_refund_draft": create_refund}
                )
            }
        )
    )
    executor = BlueprintExecutor(model=RefundRequestModel(), tools=managed)
    plan = compile_plan(example_blueprint_path)

    pending = executor.execute(
        plan,
        "为订单O-1创建100元退款草稿",
        "approval-test",
        policy_context={"customer_identity_verified": True},
        actor_roles=("customer_service",),
    )

    assert pending.status == "pending_approval"
    assert pending.answer is None
    assert calls == 0
    approval = pending.pending_approvals[0]
    assert approval.tool_id == "create_refund_draft"
    assert approval.approver_roles == ("supervisor",)

    with pytest.raises(ApprovalAuthorizationError, match="not authorized"):
        executor.resume(
            "approval-test",
            ApprovalResume(
                approval_id=approval.approval_id,
                decision=ApprovalDecision.APPROVE,
                reason="approved",
                approver_roles=("customer_service",),
            ),
        )
    assert calls == 0

    completed = executor.resume(
        "approval-test",
        ApprovalResume(
            approval_id=approval.approval_id,
            decision=ApprovalDecision.APPROVE,
            reason="金额和材料已核对",
            approver_roles=("supervisor",),
        ),
    )

    assert completed.status == "completed"
    assert completed.pending_approvals == ()
    assert completed.answer is not None
    assert calls == 1
    assert completed.tool_calls == 1
    assert executor.approval_audit.records[0].reason == "金额和材料已核对"
    assert executor.approval_audit.records[0].approver_roles == ("supervisor",)


def test_rejected_approval_never_executes_connector(example_blueprint_path: Path) -> None:
    calls = 0

    def create_refund(arguments: dict[str, object]) -> object:
        nonlocal calls
        calls += 1
        return arguments

    tools = ManagedToolExecutor(
        ConnectorRegistry(
            {
                "connector://commerce/refunds": FunctionConnector(
                    {"create_refund_draft": create_refund}
                )
            }
        )
    )
    executor = BlueprintExecutor(model=RefundRequestModel(), tools=tools)
    pending = executor.execute(
        compile_plan(example_blueprint_path),
        "创建退款草稿",
        "reject-test",
        policy_context={"customer_identity_verified": True},
        actor_roles=("customer_service",),
    )
    approval = pending.pending_approvals[0]

    result = executor.resume(
        "reject-test",
        ApprovalResume(
            approval_id=approval.approval_id,
            decision=ApprovalDecision.REJECT,
            reason="证据不足",
            approver_roles=("supervisor",),
        ),
    )

    assert result.status == "completed"
    assert calls == 0
    assert any(
        "approval_rejected" in item for report in result.reports for item in report.tool_results
    )
