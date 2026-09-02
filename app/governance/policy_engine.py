"""Evaluate compiled policy data without eval or model judgment."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.blueprint.schema import PolicyDecision
from app.compiler.intermediate import (
    ComparisonOperator,
    ConditionSpec,
    ExecutionPlan,
    PolicySpec,
)

DECISION_PRIORITY = {
    PolicyDecision.ALLOW: 0,
    PolicyDecision.REQUIRE_APPROVAL: 1,
    PolicyDecision.DENY: 2,
    PolicyDecision.TRANSFER_TO_HUMAN: 3,
}


class PolicyOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: PolicyDecision
    matched_policy_ids: tuple[str, ...]
    unmatched_policy_ids: tuple[str, ...]


class PolicyEngine:
    def evaluate(
        self, plan: ExecutionPlan, tool_id: str, facts: Mapping[str, Any]
    ) -> PolicyOutcome:
        applicable = [policy for policy in plan.policies if tool_id in policy.applies_to_tool_ids]
        if not applicable:
            return PolicyOutcome(
                decision=PolicyDecision.ALLOW,
                matched_policy_ids=(),
                unmatched_policy_ids=(),
            )

        decisions: list[PolicyDecision] = []
        matched: list[str] = []
        unmatched: list[str] = []
        for policy in applicable:
            decision = self._first_match(policy, facts)
            if decision is None:
                unmatched.append(policy.id)
                decisions.append(PolicyDecision.DENY)
            else:
                matched.append(policy.id)
                decisions.append(decision)
        return PolicyOutcome(
            decision=max(decisions, key=DECISION_PRIORITY.__getitem__),
            matched_policy_ids=tuple(matched),
            unmatched_policy_ids=tuple(unmatched),
        )

    def _first_match(self, policy: PolicySpec, facts: Mapping[str, Any]) -> PolicyDecision | None:
        for rule in policy.rules:
            found, actual = self._resolve(facts, rule.condition.field)
            if found and self._compare(actual, rule.condition):
                return rule.decision
        return None

    @staticmethod
    def _resolve(facts: Mapping[str, Any], path: str) -> tuple[bool, Any]:
        value: Any = facts
        for part in path.split("."):
            if not isinstance(value, Mapping) or part not in value:
                return False, None
            value = value[part]
        return True, value

    @staticmethod
    def _compare(actual: Any, condition: ConditionSpec) -> bool:
        expected = condition.value
        try:
            return {
                ComparisonOperator.EQUAL: lambda: actual == expected,
                ComparisonOperator.NOT_EQUAL: lambda: actual != expected,
                ComparisonOperator.LESS_THAN: lambda: actual < expected,
                ComparisonOperator.LESS_THAN_OR_EQUAL: lambda: actual <= expected,
                ComparisonOperator.GREATER_THAN: lambda: actual > expected,
                ComparisonOperator.GREATER_THAN_OR_EQUAL: lambda: actual >= expected,
            }[condition.operator]()
        except TypeError:
            return False
