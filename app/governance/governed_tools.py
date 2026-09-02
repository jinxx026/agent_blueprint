"""Apply compiled policies and LangGraph approval interrupts before tool effects."""

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from langgraph.types import interrupt

from app.blueprint.schema import PolicyDecision
from app.compiler.intermediate import ExecutionPlan, ToolBindingSpec
from app.connectors.executor import ManagedToolExecutor
from app.governance.approvals import ApprovalDecision, ApprovalRequest, ApprovalResume
from app.governance.policy_engine import PolicyEngine
from app.tooling import ToolExecutor


class GovernedToolExecutor:
    def __init__(
        self,
        plan: ExecutionPlan,
        delegate: ToolExecutor,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self._plan = plan
        self._delegate = delegate
        self._policy_engine = policy_engine or PolicyEngine()

    def execute(
        self,
        spec: ToolBindingSpec,
        arguments: Mapping[str, Any],
        *,
        agent_id: str = "unknown-agent",
        execution_id: str = "unknown-execution",
        policy_context: Mapping[str, Any] | None = None,
        actor_roles: tuple[str, ...] = (),
    ) -> str:
        if not set(actor_roles).intersection(spec.allowed_roles):
            return self._denied("actor_role_not_allowed", ())
        facts = {**dict(policy_context or {}), **dict(arguments)}
        outcome = self._policy_engine.evaluate(self._plan, spec.id, facts)
        if outcome.decision is PolicyDecision.DENY:
            return self._denied("policy_denied", outcome.matched_policy_ids)
        if outcome.decision is PolicyDecision.TRANSFER_TO_HUMAN:
            return self._denied("transfer_to_human", outcome.matched_policy_ids)

        approval_granted = False
        if outcome.decision is PolicyDecision.REQUIRE_APPROVAL or spec.approval_policy_id:
            approval = self._approval_request(spec, arguments, agent_id, execution_id, actor_roles)
            raw_resume = interrupt(approval.model_dump(mode="json"))
            resume = ApprovalResume.model_validate(raw_resume)
            if resume.approval_id != approval.approval_id:
                return self._denied("approval_id_mismatch", (approval.policy_id,))
            if not set(resume.approver_roles).intersection(approval.approver_roles):
                return self._denied("approver_not_authorized", (approval.policy_id,))
            if approval.require_reason and not resume.reason.strip():
                return self._denied("approval_reason_required", (approval.policy_id,))
            if resume.decision is ApprovalDecision.REJECT:
                return self._denied("approval_rejected", (approval.policy_id,))
            approval_granted = True

        common = {
            "agent_id": agent_id,
            "execution_id": execution_id,
            "policy_context": policy_context,
            "actor_roles": actor_roles,
        }
        if isinstance(self._delegate, ManagedToolExecutor):
            return self._delegate.execute(
                spec, arguments, approval_granted=approval_granted, **common
            )
        return self._delegate.execute(spec, arguments, **common)

    def _approval_request(
        self,
        spec: ToolBindingSpec,
        arguments: Mapping[str, Any],
        agent_id: str,
        execution_id: str,
        actor_roles: tuple[str, ...],
    ) -> ApprovalRequest:
        policy_id = spec.approval_policy_id or "runtime-policy-approval"
        approval_spec = next(
            (approval for approval in self._plan.approvals if approval.id == policy_id), None
        )
        canonical = json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)
        approval_id = hashlib.sha256(f"{execution_id}:{spec.id}:{canonical}".encode()).hexdigest()[
            :20
        ]
        return ApprovalRequest(
            approval_id=approval_id,
            execution_id=execution_id,
            policy_id=policy_id,
            tool_id=spec.id,
            agent_id=agent_id,
            arguments=dict(arguments),
            approver_roles=approval_spec.approver_roles if approval_spec else actor_roles,
            require_reason=approval_spec.require_reason if approval_spec else True,
            created_at=(created_at := datetime.now(UTC)),
            expires_at=created_at
            + self._duration(approval_spec.expires_after if approval_spec else "1h"),
            on_expire=str(approval_spec.on_expire if approval_spec else "deny"),
        )

    @staticmethod
    def _duration(value: str) -> timedelta:
        amount, unit = int(value[:-1]), value[-1]
        field = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}[unit]
        return timedelta(**{field: amount})

    @staticmethod
    def _denied(reason: str, policy_ids: tuple[str, ...]) -> str:
        return json.dumps(
            {"status": "denied", "reason": reason, "policy_ids": policy_ids},
            ensure_ascii=False,
        )
