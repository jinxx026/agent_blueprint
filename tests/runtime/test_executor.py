from pathlib import Path

import pytest

from app.blueprint.loader import BlueprintFormat
from app.blueprint.service import BlueprintService
from app.compiler import BlueprintCompiler
from app.runtime import (
    BlueprintExecutor,
    KnowledgeDocument,
    MemoryKnowledgeStore,
    MemoryToolRegistry,
)
from app.runtime.agent_factory import AgentFactory, AgentInvocation
from app.runtime.model import AgentPrompt, AgentResponse, ToolRequest


def compile_example(path: Path):
    validation = BlueprintService().validate_text(
        path.read_text(encoding="utf-8"), BlueprintFormat.YAML
    )
    assert validation.blueprint is not None
    return BlueprintCompiler().compile(validation.blueprint)


def test_supervisor_graph_runs_all_specialists_and_collects_citations(
    example_blueprint_path: Path,
) -> None:
    plan = compile_example(example_blueprint_path)
    knowledge = MemoryKnowledgeStore(
        [
            KnowledgeDocument(
                source_id="after_sales_policy",
                content="普通商品签收后七天内可以申请退款。",
                citation="policy:refund-seven-days",
            ),
            KnowledgeDocument(
                source_id="product_catalog",
                content="普通商品支持退货。",
                citation="catalog:normal-product",
            ),
        ]
    )

    result = BlueprintExecutor(knowledge=knowledge).execute(
        plan, "普通商品签收三天后能退款吗？", "test-thread"
    )

    assert [report.agent_id for report in result.reports] == [
        "policy-specialist",
        "order-specialist",
        "refund-specialist",
    ]
    assert set(result.citations) == {
        "policy:refund-seven-days",
        "catalog:normal-product",
    }
    assert result.trace[0] == "supervisor:delegate:policy-specialist"
    assert result.trace[-1] == "supervisor:complete"
    assert result.model_calls == 4
    assert "七天内" in result.answer


class UnauthorizedToolModel:
    def invoke(self, prompt: AgentPrompt) -> AgentResponse:
        return AgentResponse(
            content="try an unauthorized operation",
            tool_requests=(
                ToolRequest(
                    tool_id="create_refund_draft",
                    arguments={"order_id": "O-1", "amount": 10, "reason": "test reason"},
                ),
            ),
        )


def test_agent_cannot_call_a_tool_outside_its_compiled_permissions(
    example_blueprint_path: Path,
) -> None:
    plan = compile_example(example_blueprint_path)
    order_agent = next(agent for agent in plan.agents if agent.id == "order-specialist")
    factory = AgentFactory(
        plan,
        UnauthorizedToolModel(),
        MemoryKnowledgeStore(),
        MemoryToolRegistry({"create_refund_draft": lambda arguments: arguments}),
    )

    with pytest.raises(PermissionError, match="cannot call tool"):
        factory.build(order_agent).invoke(AgentInvocation(question="refund"))
