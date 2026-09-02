"""Cross-field Blueprint semantic validation tests."""

from copy import deepcopy
from typing import Any

from app.blueprint.service import BlueprintService


def _issue_codes(data: dict[str, Any]) -> set[str]:
    return {issue.code for issue in BlueprintService().validate_data(data).errors}


def test_high_risk_tool_requires_existing_approval(example_blueprint_data: dict[str, Any]) -> None:
    data = deepcopy(example_blueprint_data)
    data["spec"]["tools"][2]["approval_policy"] = "missing-approval"

    assert "approval_policy_not_found" in _issue_codes(data)


def test_write_tool_requires_idempotency(example_blueprint_data: dict[str, Any]) -> None:
    data = deepcopy(example_blueprint_data)
    data["spec"]["tools"][2]["idempotency_required"] = False

    assert "write_tool_requires_idempotency" in _issue_codes(data)


def test_tool_required_parameters_must_be_defined(example_blueprint_data: dict[str, Any]) -> None:
    data = deepcopy(example_blueprint_data)
    data["spec"]["tools"][0]["input_schema"]["required"].append("missing_parameter")

    assert "tool_required_parameter_not_defined" in _issue_codes(data)


def test_agent_references_must_exist(example_blueprint_data: dict[str, Any]) -> None:
    data = deepcopy(example_blueprint_data)
    data["spec"]["agents"][0]["can_delegate_to"].append("ghost-agent")

    assert "delegate_agent_not_found" in _issue_codes(data)


def test_delegation_graph_cannot_cycle(example_blueprint_data: dict[str, Any]) -> None:
    data = deepcopy(example_blueprint_data)
    data["spec"]["agents"][1]["can_delegate_to"].append("supervisor")

    assert "agent_delegation_cycle" in _issue_codes(data)


def test_resource_roles_cannot_exceed_audience(example_blueprint_data: dict[str, Any]) -> None:
    data = deepcopy(example_blueprint_data)
    data["spec"]["knowledge"][0]["allowed_roles"].append("external_user")

    assert "role_outside_audience" in _issue_codes(data)
