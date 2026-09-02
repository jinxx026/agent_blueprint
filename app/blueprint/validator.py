"""Cross-field semantic validation for already typed Blueprints."""

from collections import Counter
from collections.abc import Iterable

from app.blueprint.errors import BlueprintIssue, IssueSeverity
from app.blueprint.schema import (
    Blueprint,
    EvaluationCheck,
    OrchestrationPattern,
    RiskLevel,
    ToolEffect,
)


class BlueprintValidator:
    """Check relationships that individual Pydantic fields cannot validate."""

    def validate(self, blueprint: Blueprint) -> tuple[BlueprintIssue, ...]:
        issues: list[BlueprintIssue] = []
        spec = blueprint.spec

        issues.extend(self._duplicate_id_issues("knowledge", [item.id for item in spec.knowledge]))
        issues.extend(self._duplicate_id_issues("tools", [item.id for item in spec.tools]))
        issues.extend(self._duplicate_id_issues("agents", [item.id for item in spec.agents]))
        issues.extend(self._duplicate_id_issues("policies", [item.id for item in spec.policies]))
        issues.extend(self._duplicate_id_issues("approvals", [item.id for item in spec.approvals]))

        audience_roles = set(spec.audience.allowed_roles)
        knowledge_ids = {item.id for item in spec.knowledge}
        tool_ids = {item.id for item in spec.tools}
        agent_ids = {item.id for item in spec.agents}
        approval_ids = {item.id for item in spec.approvals}

        for index, source in enumerate(spec.knowledge):
            issues.extend(
                self._unknown_role_issues(
                    source.allowed_roles,
                    audience_roles,
                    f"spec.knowledge[{index}].allowed_roles",
                )
            )

        for index, tool in enumerate(spec.tools):
            path = f"spec.tools[{index}]"
            issues.extend(
                self._unknown_role_issues(
                    tool.allowed_roles,
                    audience_roles,
                    f"{path}.allowed_roles",
                )
            )
            properties = tool.input_schema.get("properties", {})
            required = tool.input_schema.get("required", [])
            if tool.input_schema.get("type") != "object" or not isinstance(properties, dict):
                issues.append(
                    BlueprintIssue(
                        "tool_input_schema_must_be_object",
                        f"{path}.input_schema",
                        f"Tool {tool.id!r} input schema must describe an object",
                    )
                )
            elif not isinstance(required, list) or any(
                field_name not in properties for field_name in required
            ):
                issues.append(
                    BlueprintIssue(
                        "tool_required_parameter_not_defined",
                        f"{path}.input_schema.required",
                        f"Tool {tool.id!r} has required parameters missing from properties",
                    )
                )
            if tool.effect is ToolEffect.WRITE and not tool.idempotency_required:
                issues.append(
                    BlueprintIssue(
                        "write_tool_requires_idempotency",
                        f"{path}.idempotency_required",
                        f"Write tool {tool.id!r} must require an idempotency key",
                    )
                )
            if tool.effect is ToolEffect.IRREVERSIBLE:
                issues.append(
                    BlueprintIssue(
                        "irreversible_tool_not_supported",
                        f"{path}.effect",
                        f"Irreversible tool {tool.id!r} is not supported in v1",
                    )
                )
            if tool.risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
                if tool.approval_policy is None:
                    issues.append(
                        BlueprintIssue(
                            "high_risk_tool_requires_approval",
                            f"{path}.approval_policy",
                            f"High-risk tool {tool.id!r} must reference an approval policy",
                        )
                    )
                elif tool.approval_policy not in approval_ids:
                    issues.append(
                        BlueprintIssue(
                            "approval_policy_not_found",
                            f"{path}.approval_policy",
                            f"Approval policy {tool.approval_policy!r} does not exist",
                        )
                    )

        for index, approval in enumerate(spec.approvals):
            issues.extend(
                self._unknown_role_issues(
                    approval.approver_roles,
                    audience_roles,
                    f"spec.approvals[{index}].approver_roles",
                )
            )

        for policy_index, policy in enumerate(spec.policies):
            for target_index, target in enumerate(policy.applies_to):
                if target not in tool_ids:
                    issues.append(
                        BlueprintIssue(
                            "policy_target_not_found",
                            f"spec.policies[{policy_index}].applies_to[{target_index}]",
                            f"Policy target tool {target!r} does not exist",
                        )
                    )

        for agent_index, agent in enumerate(spec.agents):
            for ref_index, knowledge_id in enumerate(agent.knowledge):
                if knowledge_id not in knowledge_ids:
                    issues.append(
                        BlueprintIssue(
                            "agent_knowledge_not_found",
                            f"spec.agents[{agent_index}].knowledge[{ref_index}]",
                            f"Agent knowledge source {knowledge_id!r} does not exist",
                        )
                    )
            for ref_index, tool_id in enumerate(agent.tools):
                if tool_id not in tool_ids:
                    issues.append(
                        BlueprintIssue(
                            "agent_tool_not_found",
                            f"spec.agents[{agent_index}].tools[{ref_index}]",
                            f"Agent tool {tool_id!r} does not exist",
                        )
                    )
            for ref_index, delegate_id in enumerate(agent.can_delegate_to):
                delegate_path = f"spec.agents[{agent_index}].can_delegate_to[{ref_index}]"
                if delegate_id == agent.id:
                    issues.append(
                        BlueprintIssue(
                            "agent_cannot_delegate_to_self",
                            delegate_path,
                            f"Agent {agent.id!r} cannot delegate to itself",
                        )
                    )
                elif delegate_id not in agent_ids:
                    issues.append(
                        BlueprintIssue(
                            "delegate_agent_not_found",
                            delegate_path,
                            f"Delegate agent {delegate_id!r} does not exist",
                        )
                    )

        if spec.orchestration.entry_agent not in agent_ids:
            issues.append(
                BlueprintIssue(
                    "entry_agent_not_found",
                    "spec.orchestration.entry_agent",
                    f"Entry agent {spec.orchestration.entry_agent!r} does not exist",
                )
            )

        issues.extend(self._delegation_cycle_issues(blueprint))

        entry_agent = next(
            (agent for agent in spec.agents if agent.id == spec.orchestration.entry_agent),
            None,
        )
        if (
            spec.orchestration.pattern is OrchestrationPattern.SUPERVISOR
            and entry_agent is not None
            and not entry_agent.can_delegate_to
        ):
            issues.append(
                BlueprintIssue(
                    "supervisor_has_no_subagents",
                    "spec.orchestration.entry_agent",
                    "Supervisor entry agent must be allowed to delegate to at least one subagent",
                )
            )
        if spec.orchestration.pattern is OrchestrationPattern.SINGLE and len(spec.agents) != 1:
            issues.append(
                BlueprintIssue(
                    "single_pattern_requires_one_agent",
                    "spec.agents",
                    "Single orchestration pattern requires exactly one agent",
                )
            )

        if spec.rag.enabled and not spec.knowledge:
            issues.append(
                BlueprintIssue(
                    "rag_requires_knowledge",
                    "spec.rag.enabled",
                    "RAG cannot be enabled without at least one knowledge source",
                )
            )
        if (
            any(source.citation_required for source in spec.knowledge)
            and not spec.rag.return_citations
        ):
            issues.append(
                BlueprintIssue(
                    "rag_must_return_citations",
                    "spec.rag.return_citations",
                    "RAG must return citations because at least one knowledge source requires them",
                )
            )

        required_checks = set(spec.evaluation.required_checks)
        for required_check in {
            EvaluationCheck.AUTHORIZATION,
            EvaluationCheck.APPROVAL_BEHAVIOR,
        }:
            if required_check not in required_checks:
                issues.append(
                    BlueprintIssue(
                        "required_safety_evaluation_missing",
                        "spec.evaluation.required_checks",
                        f"Safety evaluation {required_check.value!r} is required",
                    )
                )

        assigned_tools = {tool for agent in spec.agents for tool in agent.tools}
        for tool_id in sorted(tool_ids - assigned_tools):
            issues.append(
                BlueprintIssue(
                    "tool_not_assigned_to_agent",
                    "spec.agents",
                    f"Tool {tool_id!r} is defined but no agent can use it",
                    IssueSeverity.WARNING,
                )
            )

        return tuple(issues)

    @staticmethod
    def _duplicate_id_issues(collection: str, identifiers: Iterable[str]) -> list[BlueprintIssue]:
        return [
            BlueprintIssue(
                "duplicate_id",
                f"spec.{collection}",
                f"Duplicate ID {identifier!r} in {collection}",
            )
            for identifier, count in Counter(identifiers).items()
            if count > 1
        ]

    @staticmethod
    def _unknown_role_issues(
        roles: Iterable[str],
        audience_roles: set[str],
        path: str,
    ) -> list[BlueprintIssue]:
        return [
            BlueprintIssue(
                "role_outside_audience",
                path,
                f"Role {role!r} is not present in spec.audience.allowed_roles",
            )
            for role in roles
            if role not in audience_roles
        ]

    @staticmethod
    def _delegation_cycle_issues(blueprint: Blueprint) -> list[BlueprintIssue]:
        graph = {agent.id: set(agent.can_delegate_to) for agent in blueprint.spec.agents}
        visited: set[str] = set()
        active: set[str] = set()

        def has_cycle(agent_id: str) -> bool:
            if agent_id in active:
                return True
            if agent_id in visited:
                return False
            active.add(agent_id)
            for delegate_id in graph.get(agent_id, set()):
                if delegate_id in graph and has_cycle(delegate_id):
                    return True
            active.remove(agent_id)
            visited.add(agent_id)
            return False

        if any(has_cycle(agent_id) for agent_id in graph):
            return [
                BlueprintIssue(
                    "agent_delegation_cycle",
                    "spec.agents",
                    "Agent delegation graph must not contain a cycle",
                )
            ]
        return []
