"""Typed implementation of the AgentBlueprint v0.1 specification."""

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Identifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_-]*$",
    ),
]
NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2_000),
]
SemanticVersion = Annotated[
    str,
    StringConstraints(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$"),
]
Duration = Annotated[str, StringConstraints(pattern=r"^[1-9]\d*[smhd]$")]


class StrictModel(BaseModel):
    """Base model that rejects unknown fields and is immutable after parsing."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class KnowledgeType(StrEnum):
    DOCUMENTS = "documents"
    DATABASE = "database"
    API = "api"


class ToolEffect(StrEnum):
    READ = "read"
    WRITE = "write"
    IRREVERSIBLE = "irreversible"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    TRANSFER_TO_HUMAN = "transfer_to_human"


class ApprovalExpiryAction(StrEnum):
    DENY = "deny"
    TRANSFER_TO_HUMAN = "transfer_to_human"


class FallbackAction(StrEnum):
    ASK_USER = "ask_user"
    RETRY = "retry"
    DENY = "deny"
    TRANSFER_TO_HUMAN = "transfer_to_human"
    STOP = "stop"


class RagStrategy(StrEnum):
    TWO_STEP = "two_step"
    AGENTIC = "agentic"
    HYBRID = "hybrid"


class OrchestrationPattern(StrEnum):
    SINGLE = "single"
    SUPERVISOR = "supervisor"
    ROUTER = "router"
    HANDOFF = "handoff"
    CUSTOM = "custom"


class EvaluationCheck(StrEnum):
    FINAL_ANSWER = "final_answer"
    CITATIONS = "citations"
    TOOL_TRAJECTORY = "tool_trajectory"
    AUTHORIZATION = "authorization"
    APPROVAL_BEHAVIOR = "approval_behavior"


class Metadata(StrictModel):
    name: Identifier
    display_name: NonEmptyText
    version: SemanticVersion
    description: NonEmptyText
    labels: dict[str, str] = Field(default_factory=dict)


class Identity(StrictModel):
    role: NonEmptyText
    goal: NonEmptyText
    responsibilities: list[NonEmptyText] = Field(min_length=1)
    prohibited_actions: list[NonEmptyText] = Field(min_length=1)
    success_definition: list[NonEmptyText] = Field(min_length=1)


class Audience(StrictModel):
    allowed_roles: list[Identifier] = Field(min_length=1)
    default_language: Annotated[
        str,
        StringConstraints(pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$"),
    ] = "zh-CN"


class KnowledgeSource(StrictModel):
    id: Identifier
    type: KnowledgeType
    description: NonEmptyText
    source_ref: NonEmptyText
    allowed_roles: list[Identifier] = Field(min_length=1)
    citation_required: bool
    freshness: Duration | None = None


class RagConfig(StrictModel):
    enabled: bool = True
    strategy: RagStrategy = RagStrategy.AGENTIC
    default_top_k: int = Field(default=6, ge=1, le=50)
    rerank: bool = True
    return_citations: bool = True


class ToolDefinition(StrictModel):
    id: Identifier
    description: NonEmptyText
    connector_ref: NonEmptyText
    operation: Identifier
    effect: ToolEffect
    risk: RiskLevel
    allowed_roles: list[Identifier] = Field(min_length=1)
    input_schema: dict[str, Any]
    idempotency_required: bool
    approval_policy: Identifier | None


class AgentDefinition(StrictModel):
    id: Identifier
    display_name: NonEmptyText
    role: NonEmptyText
    goal: NonEmptyText
    knowledge: list[Identifier] = Field(default_factory=list)
    tools: list[Identifier] = Field(default_factory=list)
    can_delegate_to: list[Identifier] = Field(default_factory=list)


class OrchestrationConfig(StrictModel):
    framework: Literal["langgraph"] = "langgraph"
    pattern: OrchestrationPattern = OrchestrationPattern.SUPERVISOR
    entry_agent: Identifier
    parallel_delegation: bool = False
    human_in_the_loop: bool = True


class PolicyRule(StrictModel):
    condition: NonEmptyText = Field(alias="when")
    decision: PolicyDecision


class PolicyDefinition(StrictModel):
    id: Identifier
    description: NonEmptyText
    applies_to: list[Identifier] = Field(min_length=1)
    rules: list[PolicyRule] = Field(min_length=1)


class ApprovalPolicy(StrictModel):
    id: Identifier
    approver_roles: list[Identifier] = Field(min_length=1)
    expires_after: Duration
    on_expire: ApprovalExpiryAction
    require_reason: bool


class ToolFailureFallback(StrictModel):
    action: FallbackAction
    max_attempts: int = Field(default=1, ge=0, le=5)


class FallbackConfig(StrictModel):
    missing_information: FallbackAction
    conflicting_knowledge: FallbackAction
    tool_failure: ToolFailureFallback
    unsafe_request: FallbackAction


class RuntimeConfig(StrictModel):
    max_steps: int = Field(ge=1, le=100)
    timeout_seconds: int = Field(ge=1, le=3_600)
    max_model_calls: int = Field(ge=1, le=100)
    max_tool_calls: int = Field(ge=0, le=100)
    require_structured_output: bool = True


class EvaluationConfig(StrictModel):
    dataset_ref: NonEmptyText
    minimum_score: float = Field(ge=0, le=1)
    required_checks: list[EvaluationCheck] = Field(min_length=1)


class BlueprintSpec(StrictModel):
    identity: Identity
    audience: Audience
    knowledge: list[KnowledgeSource] = Field(default_factory=list)
    rag: RagConfig
    tools: list[ToolDefinition] = Field(default_factory=list)
    agents: list[AgentDefinition] = Field(min_length=1)
    orchestration: OrchestrationConfig
    policies: list[PolicyDefinition] = Field(default_factory=list)
    approvals: list[ApprovalPolicy] = Field(default_factory=list)
    fallback: FallbackConfig
    runtime: RuntimeConfig
    evaluation: EvaluationConfig


class Blueprint(StrictModel):
    """Root object accepted by the v0.1 Compiler boundary."""

    api_version: Literal["agentblueprint.dev/v0.1"]
    kind: Literal["AgentBlueprint"]
    metadata: Metadata
    spec: BlueprintSpec
