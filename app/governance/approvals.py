"""Serializable approval request and resume contracts."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    approval_id: str
    execution_id: str
    policy_id: str
    tool_id: str
    agent_id: str
    arguments: dict[str, Any]
    approver_roles: tuple[str, ...]
    require_reason: bool
    created_at: datetime
    expires_at: datetime
    on_expire: str


class ApprovalResume(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    approval_id: str
    decision: ApprovalDecision
    reason: str = ""
    approver_roles: tuple[str, ...]


class ApprovalAuthorizationError(PermissionError):
    pass


class ApprovalExpiredError(PermissionError):
    pass


class ApprovalAuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    occurred_at: datetime
    thread_id: str
    approval_id: str
    decision: ApprovalDecision
    reason: str
    approver_roles: tuple[str, ...]


class MemoryApprovalAuditSink:
    def __init__(self) -> None:
        self._records: list[ApprovalAuditRecord] = []

    def record(self, thread_id: str, decision: ApprovalResume) -> None:
        self._records.append(
            ApprovalAuditRecord(
                occurred_at=datetime.now(UTC),
                thread_id=thread_id,
                approval_id=decision.approval_id,
                decision=decision.decision,
                reason=decision.reason,
                approver_roles=decision.approver_roles,
            )
        )

    @property
    def records(self) -> tuple[ApprovalAuditRecord, ...]:
        return tuple(self._records)
