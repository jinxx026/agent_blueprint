"""Immutable intermediate representation produced by the Blueprint Compiler."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.blueprint.schema import (
    ApprovalExpiryAction,
    EvaluationCheck,
    OrchestrationPattern,
    PolicyDecision,
    RagStrategy,
    RiskLevel,
    ToolEffect,
)


class ImmutableModel(BaseModel):
    """Strict serializable base for deterministic Compiler output."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ComparisonOperator(StrEnum):
    EQUAL = "=="
    NOT_EQUAL = "!="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="


class GraphNodeKind(StrEnum):
    AGENT = "agent"


class GraphEdgeKind(StrEnum):
    START = "start"
    DELEGATE = "delegate"
    RETURN = "return"
    ROUTE = "route"
    HANDOFF = "handoff"
    COMPLETE = "complete"


class PlanSource(ImmutableModel):
    blueprint_name: str
    blueprint_version: str
    api_version: str
    content_hash: str


class AgentSpec(ImmutableModel):
    id: str
    display_name: str
    role: str
    goal: str
    system_instruction: str
    knowledge_source_ids: tuple[str, ...]
    tool_ids: tuple[str, ...]
    delegate_to: tuple[str, ...]


class RetrieverSpec(ImmutableModel):
    id: str
    agent_id: str
    strategy: RagStrategy
    source_ids: tuple[str, ...]
    top_k: int
    rerank: bool
    return_citations: bool


class ToolBindingSpec(ImmutableModel):
    id: str
    connector_ref: str
    operation: str
    effect: ToolEffect
    risk: RiskLevel
    allowed_roles: tuple[str, ...]
    assigned_agent_ids: tuple[str, ...]
    input_schema_json: str
    idempotency_required: bool
    approval_policy_id: str | None


class ConditionSpec(ImmutableModel):
    field: str
    operator: ComparisonOperator
    value: bool | int | float | str | None


class PolicyRuleSpec(ImmutableModel):
    condition: ConditionSpec
    decision: PolicyDecision


class PolicySpec(ImmutableModel):
    id: str
    applies_to_tool_ids: tuple[str, ...]
    rules: tuple[PolicyRuleSpec, ...]


class ApprovalSpec(ImmutableModel):
    id: str
    approver_roles: tuple[str, ...]
    expires_after: str
    on_expire: ApprovalExpiryAction
    require_reason: bool


class GraphNodeSpec(ImmutableModel):
    id: str
    kind: GraphNodeKind
    agent_id: str


class GraphEdgeSpec(ImmutableModel):
    source: str
    target: str
    kind: GraphEdgeKind
    trigger: str


class GraphPlan(ImmutableModel):
    pattern: OrchestrationPattern
    entry_node: str
    nodes: tuple[GraphNodeSpec, ...]
    edges: tuple[GraphEdgeSpec, ...]
    parallel_delegation: bool
    human_in_the_loop: bool


class ExecutionLimits(ImmutableModel):
    max_steps: int
    timeout_seconds: int
    max_model_calls: int
    max_tool_calls: int
    require_structured_output: bool


class EvaluationPlan(ImmutableModel):
    dataset_ref: str
    minimum_score: float
    required_checks: tuple[EvaluationCheck, ...]


class ExecutionPlan(ImmutableModel):
    """Portable result consumed by future LangGraph and test adapters."""

    schema_version: Literal["executionplan.agentblueprint.dev/v0.1"]
    compiler_version: Literal["0.1.0"]
    plan_id: str
    source: PlanSource
    agents: tuple[AgentSpec, ...]
    retrievers: tuple[RetrieverSpec, ...]
    tools: tuple[ToolBindingSpec, ...]
    policies: tuple[PolicySpec, ...]
    approvals: tuple[ApprovalSpec, ...]
    graph: GraphPlan
    limits: ExecutionLimits
    evaluation: EvaluationPlan
