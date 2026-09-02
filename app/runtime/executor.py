"""Application service that executes one compiled Blueprint request."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from langgraph.types import Command
from pydantic import BaseModel, ConfigDict

from app.compiler.intermediate import ExecutionPlan
from app.governance.approvals import (
    ApprovalAuthorizationError,
    ApprovalExpiredError,
    ApprovalRequest,
    ApprovalResume,
    MemoryApprovalAuditSink,
)
from app.governance.governed_tools import GovernedToolExecutor
from app.runtime.agent_factory import AgentFactory
from app.runtime.checkpoints import create_checkpointer
from app.runtime.graph_builder import RuntimeGraphBuilder
from app.runtime.model import AgentModel, DeterministicAgentModel
from app.runtime.retrievers import KnowledgeRetriever, MemoryKnowledgeStore
from app.runtime.state import AgentReport, RuntimeState
from app.runtime.tools import MemoryToolRegistry
from app.tooling import ToolExecutor


class ExecutionStatus(StrEnum):
    COMPLETED = "completed"
    PENDING_APPROVAL = "pending_approval"


class ExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    plan_id: str
    thread_id: str
    status: ExecutionStatus
    answer: str | None
    pending_approvals: tuple[ApprovalRequest, ...] = ()
    reports: tuple[AgentReport, ...]
    citations: tuple[str, ...]
    trace: tuple[str, ...]
    model_calls: int
    tool_calls: int


@dataclass
class _ExecutionSession:
    plan: ExecutionPlan
    graph: Any
    pending_approvals: tuple[ApprovalRequest, ...] = ()


class BlueprintExecutor:
    """Compose adapters, build LangGraph, and run it with explicit limits."""

    def __init__(
        self,
        model: AgentModel | None = None,
        knowledge: KnowledgeRetriever | None = None,
        tools: ToolExecutor | None = None,
    ) -> None:
        self._model = model or DeterministicAgentModel()
        self._knowledge = knowledge or MemoryKnowledgeStore()
        self._tools = tools or MemoryToolRegistry()
        self._checkpointer = create_checkpointer()
        self._sessions: dict[str, _ExecutionSession] = {}
        self._approval_audit = MemoryApprovalAuditSink()

    @property
    def approval_audit(self) -> MemoryApprovalAuditSink:
        return self._approval_audit

    def execute(
        self,
        plan: ExecutionPlan,
        question: str,
        thread_id: str | None = None,
        *,
        policy_context: Mapping[str, object] | None = None,
        actor_roles: tuple[str, ...] = (),
        knowledge: KnowledgeRetriever | None = None,
        tools: ToolExecutor | None = None,
    ) -> ExecutionResult:
        resolved_thread_id = thread_id or str(uuid4())
        selected_tools = tools or self._tools
        governed_tools = GovernedToolExecutor(plan, selected_tools)
        factory = AgentFactory(plan, self._model, knowledge or self._knowledge, governed_tools)
        runnables = {agent.id: factory.build(agent) for agent in plan.agents}
        graph = RuntimeGraphBuilder().build(plan, runnables, self._checkpointer)
        session = _ExecutionSession(plan=plan, graph=graph)
        self._sessions[resolved_thread_id] = session
        initial_state: RuntimeState = {
            "question": question,
            "execution_id": resolved_thread_id,
            "policy_context": dict(policy_context or {}),
            "actor_roles": actor_roles,
            "pending_agents": RuntimeGraphBuilder.initial_workers(plan),
            "reports": [],
            "trace": [],
            "model_calls": 0,
            "tool_calls": 0,
        }
        result = graph.invoke(
            initial_state,
            config={
                "configurable": {"thread_id": resolved_thread_id},
                "recursion_limit": plan.limits.max_steps + 2,
            },
        )
        return self._to_result(session, resolved_thread_id, result)

    def resume(self, thread_id: str, decision: ApprovalResume) -> ExecutionResult:
        session = self._sessions.get(thread_id)
        if session is None or not session.pending_approvals:
            raise KeyError(f"No pending execution found for thread '{thread_id}'")
        pending = session.pending_approvals[0]
        if decision.approval_id != pending.approval_id:
            raise ApprovalAuthorizationError("Approval ID does not match pending action")
        if not set(decision.approver_roles).intersection(pending.approver_roles):
            raise ApprovalAuthorizationError("Approver role is not authorized")
        if pending.require_reason and not decision.reason.strip():
            raise ApprovalAuthorizationError("Approval reason is required")
        if datetime.now(UTC) >= pending.expires_at:
            raise ApprovalExpiredError(
                f"Approval expired; configured action is '{pending.on_expire}'"
            )
        self._approval_audit.record(thread_id, decision)
        result = session.graph.invoke(
            Command(resume=decision.model_dump(mode="json")),
            config={
                "configurable": {"thread_id": thread_id},
                "recursion_limit": session.plan.limits.max_steps + 2,
            },
        )
        return self._to_result(session, thread_id, result)

    @staticmethod
    def _to_result(
        session: _ExecutionSession, thread_id: str, result: dict[str, Any]
    ) -> ExecutionResult:
        raw_interrupts = result.get("__interrupt__", ())
        approvals = tuple(ApprovalRequest.model_validate(item.value) for item in raw_interrupts)
        session.pending_approvals = approvals
        reports = tuple(result.get("reports", ()))
        citations = tuple(dict.fromkeys(c for report in reports for c in report.citations))
        return ExecutionResult(
            plan_id=session.plan.plan_id,
            thread_id=thread_id,
            status=(ExecutionStatus.PENDING_APPROVAL if approvals else ExecutionStatus.COMPLETED),
            answer=result.get("final_answer"),
            pending_approvals=approvals,
            reports=reports,
            citations=citations,
            trace=tuple(result["trace"]),
            model_calls=result.get("model_calls", 0),
            tool_calls=result.get("tool_calls", 0),
        )
