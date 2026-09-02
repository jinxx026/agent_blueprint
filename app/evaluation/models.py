"""Typed evaluation cases and release-gate reports."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.blueprint.schema import EvaluationCheck


class EvaluationOutcome(StrEnum):
    COMPLETED = "completed"
    NEEDS_USER_INPUT = "needs_user_input"
    DENIED = "denied"
    WAITING_APPROVAL = "waiting_approval"
    TRANSFERRED_TO_HUMAN = "transferred_to_human"
    ERROR = "error"


class EvaluationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    message: str = Field(min_length=1, max_length=20_000)
    actor_role: str = Field(min_length=1, max_length=64)


class EvaluationExpected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome: EvaluationOutcome
    answer_contains: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    approval_required: bool = False
    requested_tool: str | None = None
    approver_role: str | None = None
    must_cite: tuple[str, ...] = ()
    max_model_calls: int | None = Field(default=None, ge=0)
    max_tool_calls: int | None = Field(default=None, ge=0)


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=2_000)
    input: EvaluationInput
    fixtures: dict[str, object] = Field(default_factory=dict)
    expected: EvaluationExpected


class CheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    check: EvaluationCheck
    passed: bool
    message: str


class EvaluationObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome: EvaluationOutcome
    answer: str | None = None
    citations: tuple[str, ...] = ()
    tool_calls: tuple[str, ...] = ()
    pending_tool_ids: tuple[str, ...] = ()
    approver_roles: tuple[str, ...] = ()
    model_calls: int = 0
    error: str | None = None


class EvaluationCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    description: str
    passed: bool
    score: float
    checks: tuple[CheckResult, ...]
    observation: EvaluationObservation


class ReleaseGateReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    plan_id: str
    dataset_ref: str
    score: float
    minimum_score: float
    passed: bool
    blockers: tuple[str, ...]
    cases: tuple[EvaluationCaseResult, ...]
