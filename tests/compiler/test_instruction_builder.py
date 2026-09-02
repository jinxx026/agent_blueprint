"""Generated instruction boundary tests."""

from typing import Any

from app.blueprint.schema import Blueprint
from app.compiler import BlueprintCompiler


def test_each_agent_receives_only_assigned_resources(
    example_blueprint_data: dict[str, Any],
) -> None:
    plan = BlueprintCompiler().compile(Blueprint.model_validate(example_blueprint_data))
    agents = {agent.id: agent for agent in plan.agents}

    supervisor_instruction = agents["supervisor"].system_instruction
    policy_instruction = agents["policy-specialist"].system_instruction
    refund_instruction = agents["refund-specialist"].system_instruction

    assert "Knowledge sources: none" in supervisor_instruction
    assert "Business tools: none" in supervisor_instruction
    assert "after_sales_policy, product_catalog" in policy_instruction
    assert "create_refund_draft" in refund_instruction
    assert "get_order" not in refund_instruction


def test_supervisor_instruction_describes_allowed_delegates(
    example_blueprint_data: dict[str, Any],
) -> None:
    plan = BlueprintCompiler().compile(Blueprint.model_validate(example_blueprint_data))
    supervisor = next(agent for agent in plan.agents if agent.id == "supervisor")

    assert "# Delegation" in supervisor.system_instruction
    assert "policy-specialist" in supervisor.system_instruction
    assert "order-specialist" in supervisor.system_instruction
    assert "refund-specialist" in supervisor.system_instruction
