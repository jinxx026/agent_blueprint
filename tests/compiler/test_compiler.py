"""End-to-end framework-independent Compiler tests."""

from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from app.blueprint.schema import Blueprint
from app.compiler import BlueprintCompiler, CompilationError
from app.compiler.intermediate import ComparisonOperator, GraphEdgeKind


def _compile(data: dict[str, Any]):  # type: ignore[no-untyped-def]
    return BlueprintCompiler().compile(Blueprint.model_validate(data))


def test_compiler_builds_multi_agent_execution_plan(
    example_blueprint_data: dict[str, Any],
) -> None:
    plan = _compile(example_blueprint_data)

    assert plan.schema_version == "executionplan.agentblueprint.dev/v0.1"
    assert len(plan.agents) == 4
    assert len(plan.retrievers) == 2
    assert len(plan.graph.nodes) == 4
    assert len(plan.graph.edges) == 8
    assert plan.graph.entry_node == "supervisor"
    assert sum(edge.kind is GraphEdgeKind.DELEGATE for edge in plan.graph.edges) == 3


def test_compiler_output_is_deterministic(example_blueprint_data: dict[str, Any]) -> None:
    first = _compile(example_blueprint_data)
    second = _compile(example_blueprint_data)

    assert first == second
    assert first.source.content_hash == second.source.content_hash
    assert first.plan_id == second.plan_id


def test_compiler_hash_changes_with_business_content(
    example_blueprint_data: dict[str, Any],
) -> None:
    changed = deepcopy(example_blueprint_data)
    changed["spec"]["identity"]["goal"] = "不同的业务目标"

    original_plan = _compile(example_blueprint_data)
    changed_plan = _compile(changed)

    assert original_plan.source.content_hash != changed_plan.source.content_hash
    assert original_plan.plan_id != changed_plan.plan_id


def test_compiler_preserves_least_privilege_bindings(
    example_blueprint_data: dict[str, Any],
) -> None:
    plan = _compile(example_blueprint_data)
    tools = {tool.id: tool for tool in plan.tools}
    retrievers = {retriever.agent_id: retriever for retriever in plan.retrievers}

    assert tools["create_refund_draft"].assigned_agent_ids == ("refund-specialist",)
    assert tools["create_refund_draft"].approval_policy_id == "supervisor-refund-approval"
    assert '"amount"' in tools["create_refund_draft"].input_schema_json
    assert retrievers["policy-specialist"].source_ids == (
        "after_sales_policy",
        "product_catalog",
    )
    assert retrievers["refund-specialist"].source_ids == ("after_sales_policy",)


def test_compiler_parses_policy_conditions_without_eval(
    example_blueprint_data: dict[str, Any],
) -> None:
    plan = _compile(example_blueprint_data)
    policies = {policy.id: policy for policy in plan.policies}

    identity_condition = policies["verified-identity-required"].rules[0].condition
    amount_condition = policies["refund-amount-policy"].rules[0].condition

    assert identity_condition.field == "customer_identity_verified"
    assert identity_condition.operator is ComparisonOperator.EQUAL
    assert identity_condition.value is True
    assert amount_condition.field == "amount"
    assert amount_condition.operator is ComparisonOperator.LESS_THAN_OR_EQUAL
    assert amount_condition.value == 5000


def test_compiler_rejects_unsupported_policy_language(
    example_blueprint_data: dict[str, Any],
) -> None:
    data = deepcopy(example_blueprint_data)
    data["spec"]["policies"][0]["rules"][0]["when"] = "amount in [100, 200]"
    blueprint = Blueprint.model_validate(data)

    with pytest.raises(CompilationError) as exc_info:
        BlueprintCompiler().compile(blueprint)

    assert exc_info.value.diagnostics[0].code == "unsupported_policy_condition"


def test_compiler_rejects_custom_graph_in_v01(
    example_blueprint_data: dict[str, Any],
) -> None:
    data = deepcopy(example_blueprint_data)
    data["spec"]["orchestration"]["pattern"] = "custom"
    blueprint = Blueprint.model_validate(data)

    with pytest.raises(CompilationError) as exc_info:
        BlueprintCompiler().compile(blueprint)

    assert exc_info.value.diagnostics[0].code == "custom_graph_not_supported"


def test_execution_plan_is_immutable(example_blueprint_data: dict[str, Any]) -> None:
    plan = _compile(example_blueprint_data)

    with pytest.raises(ValidationError):
        plan.plan_id = "changed"  # type: ignore[misc]
