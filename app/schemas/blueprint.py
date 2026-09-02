"""HTTP contracts for Blueprint validation."""

from pydantic import BaseModel, ConfigDict, Field

from app.blueprint.errors import BlueprintIssue, IssueSeverity
from app.blueprint.loader import MAX_BLUEPRINT_BYTES, BlueprintFormat
from app.blueprint.schema import Blueprint, OrchestrationPattern, RagStrategy
from app.blueprint.service import BlueprintValidationResult
from app.compiler.diagnostics import CompilationDiagnostic
from app.compiler.intermediate import ExecutionPlan
from app.evaluation import EvaluationCase, ReleaseGateReport
from app.governance.approvals import ApprovalDecision
from app.rag.models import RagDocument
from app.runtime.executor import ExecutionResult
from app.runtime.retrievers import KnowledgeDocument


class BlueprintValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=MAX_BLUEPRINT_BYTES)
    format: BlueprintFormat


class BlueprintIssueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    path: str
    message: str
    severity: IssueSeverity

    @classmethod
    def from_domain(cls, issue: BlueprintIssue) -> "BlueprintIssueResponse":
        return cls(
            code=issue.code,
            path=issue.path,
            message=issue.message,
            severity=issue.severity,
        )

    @classmethod
    def from_compiler(cls, diagnostic: CompilationDiagnostic) -> "BlueprintIssueResponse":
        return cls(
            code=diagnostic.code,
            path=diagnostic.path,
            message=diagnostic.message,
            severity=IssueSeverity.ERROR,
        )


class BlueprintSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    knowledge_sources: int
    tools: int
    agents: int
    rag_strategy: RagStrategy
    orchestration_pattern: OrchestrationPattern

    @classmethod
    def from_blueprint(cls, blueprint: Blueprint) -> "BlueprintSummary":
        return cls(
            name=blueprint.metadata.name,
            version=blueprint.metadata.version,
            knowledge_sources=len(blueprint.spec.knowledge),
            tools=len(blueprint.spec.tools),
            agents=len(blueprint.spec.agents),
            rag_strategy=blueprint.spec.rag.strategy,
            orchestration_pattern=blueprint.spec.orchestration.pattern,
        )


class BlueprintValidationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    blueprint: BlueprintSummary | None
    errors: list[BlueprintIssueResponse]
    warnings: list[BlueprintIssueResponse]

    @classmethod
    def from_domain(cls, result: BlueprintValidationResult) -> "BlueprintValidationResponse":
        return cls(
            valid=result.is_valid,
            blueprint=(
                BlueprintSummary.from_blueprint(result.blueprint) if result.blueprint else None
            ),
            errors=[BlueprintIssueResponse.from_domain(issue) for issue in result.errors],
            warnings=[BlueprintIssueResponse.from_domain(issue) for issue in result.warnings],
        )


class BlueprintCompilationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compiled: bool
    plan: ExecutionPlan | None
    errors: list[BlueprintIssueResponse]
    warnings: list[BlueprintIssueResponse]


class BlueprintExecutionRequest(BlueprintValidationRequest):
    message: str = Field(min_length=1, max_length=20_000)
    thread_id: str | None = Field(default=None, min_length=1, max_length=128)
    knowledge_documents: list[KnowledgeDocument] = Field(default_factory=list)
    rag_documents: list[RagDocument] = Field(default_factory=list)
    tenant_id: str = Field(default="default", min_length=1, max_length=128)
    user_roles: list[str] = Field(default_factory=list)
    policy_context: dict[str, object] = Field(default_factory=dict)


class BlueprintExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executed: bool
    result: ExecutionResult | None
    errors: list[BlueprintIssueResponse]
    warnings: list[BlueprintIssueResponse]


class BlueprintReleaseCheckRequest(BlueprintValidationRequest):
    cases: tuple[EvaluationCase, ...] = Field(min_length=1, max_length=500)
    knowledge_documents: tuple[KnowledgeDocument, ...] = ()
    rag_documents: tuple[RagDocument, ...] = ()
    tenant_id: str = Field(default="default", min_length=1, max_length=128)


class BlueprintReleaseCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluated: bool
    report: ReleaseGateReport | None
    errors: list[BlueprintIssueResponse]
    warnings: list[BlueprintIssueResponse]


class ApprovalResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(min_length=1, max_length=128)
    decision: ApprovalDecision
    reason: str = Field(default="", max_length=2_000)
    approver_roles: tuple[str, ...] = ()
