from pathlib import Path

from app.blueprint.loader import BlueprintFormat
from app.blueprint.service import BlueprintService
from app.compiler import BlueprintCompiler
from app.evaluation import EvaluationCase, EvaluationRunner
from app.runtime import BlueprintExecutor, KnowledgeDocument, MemoryToolRegistry
from app.runtime.model import AgentPrompt, AgentResponse, ToolRequest


def load_blueprint_and_plan(path: Path):
    validation = BlueprintService().validate_text(
        path.read_text(encoding="utf-8"), BlueprintFormat.YAML
    )
    assert validation.blueprint is not None
    return validation.blueprint, BlueprintCompiler().compile(validation.blueprint)


def test_passing_suite_opens_release_gate(example_blueprint_path: Path) -> None:
    blueprint, plan = load_blueprint_and_plan(example_blueprint_path)
    case = EvaluationCase.model_validate(
        {
            "id": "refund-policy-answer",
            "description": "授权客服应得到带引用的政策答案",
            "input": {"actor_role": "customer_service", "message": "七天内可以退款吗？"},
            "expected": {
                "outcome": "completed",
                "must_cite": ["after_sales_policy"],
                "approval_required": False,
            },
        }
    )
    report = EvaluationRunner(BlueprintExecutor()).run(
        blueprint,
        plan,
        (case,),
        knowledge_documents=(
            KnowledgeDocument(
                source_id="after_sales_policy",
                content="普通商品七天内可以退款。",
                citation="kb:after_sales_policy:seven-days",
            ),
        ),
    )

    assert report.passed is True
    assert report.score == 1.0
    assert report.blockers == ()


def test_failed_authorization_is_a_release_blocker(example_blueprint_path: Path) -> None:
    blueprint, plan = load_blueprint_and_plan(example_blueprint_path)
    case = EvaluationCase.model_validate(
        {
            "id": "sales-must-not-run",
            "description": "未授权角色不能运行客服智能体",
            "input": {"actor_role": "sales", "message": "查询订单"},
            "expected": {"outcome": "completed", "approval_required": False},
        }
    )

    report = EvaluationRunner(BlueprintExecutor()).run(blueprint, plan, (case,))

    assert report.passed is False
    assert any("authorization" in blocker for blocker in report.blockers)


class RefundApprovalModel:
    def invoke(self, prompt: AgentPrompt) -> AgentResponse:
        if prompt.prior_reports:
            return AgentResponse(content="汇总完成")
        if prompt.agent.id == "refund-specialist":
            return AgentResponse(
                content="请求退款草稿",
                tool_requests=(
                    ToolRequest(
                        tool_id="create_refund_draft",
                        arguments={
                            "order_id": "O-EVAL",
                            "amount": 100,
                            "reason": "customer request",
                        },
                    ),
                ),
            )
        return AgentResponse(content="检查完成")


def test_approval_and_pending_tool_are_evaluated(example_blueprint_path: Path) -> None:
    blueprint, plan = load_blueprint_and_plan(example_blueprint_path)
    executor = BlueprintExecutor(
        model=RefundApprovalModel(),
        tools=MemoryToolRegistry({"create_refund_draft": lambda arguments: arguments}),
    )
    case = EvaluationCase.model_validate(
        {
            "id": "refund-needs-approval",
            "description": "退款草稿必须暂停等待主管审批",
            "input": {"actor_role": "customer_service", "message": "创建100元退款草稿"},
            "fixtures": {"customer_identity_verified": True},
            "expected": {
                "outcome": "waiting_approval",
                "required_tools": ["create_refund_draft"],
                "approval_required": True,
                "requested_tool": "create_refund_draft",
                "approver_role": "supervisor",
                "must_cite": ["after_sales_policy"],
            },
        }
    )

    report = EvaluationRunner(executor).run(
        blueprint,
        plan,
        (case,),
        knowledge_documents=(
            KnowledgeDocument(
                source_id="after_sales_policy",
                content="退款草稿需要主管审批。",
                citation="kb:after_sales_policy:approval",
            ),
        ),
    )

    assert report.passed is True
    observation = report.cases[0].observation
    assert observation.pending_tool_ids == ("create_refund_draft",)
    assert observation.approver_roles == ("supervisor",)
