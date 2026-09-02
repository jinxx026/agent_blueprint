"""Compile the restricted policy condition language without using eval."""

import json
import re

from app.blueprint.schema import Blueprint
from app.compiler.diagnostics import CompilationDiagnostic, CompilationError
from app.compiler.intermediate import (
    ComparisonOperator,
    ConditionSpec,
    PolicyRuleSpec,
    PolicySpec,
)

_CONDITION_PATTERN = re.compile(
    r"^(?P<field>[A-Za-z_][A-Za-z0-9_.]*)\s*"
    r"(?P<operator>==|!=|<=|>=|<|>)\s*"
    r"(?P<value>.+)$"
)


class PolicyCompiler:
    """Turn simple comparisons into data that a deterministic policy engine can execute."""

    def compile(self, blueprint: Blueprint) -> tuple[PolicySpec, ...]:
        compiled: list[PolicySpec] = []
        diagnostics: list[CompilationDiagnostic] = []

        for policy_index, policy in enumerate(blueprint.spec.policies):
            rules: list[PolicyRuleSpec] = []
            for rule_index, rule in enumerate(policy.rules):
                path = f"spec.policies[{policy_index}].rules[{rule_index}].when"
                try:
                    condition = self._parse_condition(rule.condition)
                except ValueError as exc:
                    diagnostics.append(
                        CompilationDiagnostic("unsupported_policy_condition", path, str(exc))
                    )
                    continue
                rules.append(PolicyRuleSpec(condition=condition, decision=rule.decision))

            compiled.append(
                PolicySpec(
                    id=policy.id,
                    applies_to_tool_ids=tuple(policy.applies_to),
                    rules=tuple(rules),
                )
            )

        if diagnostics:
            raise CompilationError(tuple(diagnostics))
        return tuple(compiled)

    def _parse_condition(self, expression: str) -> ConditionSpec:
        match = _CONDITION_PATTERN.fullmatch(expression.strip())
        if match is None:
            raise ValueError(f"Unsupported policy condition: {expression!r}")

        raw_value = match.group("value").strip()
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Policy values must be JSON literals: number, boolean, null, or quoted string"
            ) from exc

        if isinstance(value, (dict, list)):
            raise ValueError("Policy comparison values cannot be objects or arrays")

        return ConditionSpec(
            field=match.group("field"),
            operator=ComparisonOperator(match.group("operator")),
            value=value,
        )
