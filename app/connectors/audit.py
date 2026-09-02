"""Credential-free tool audit events."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class AuditStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REUSED = "reused"


class ToolAuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    occurred_at: datetime
    execution_id: str
    agent_id: str
    tool_id: str
    connector_ref: str
    operation: str
    argument_names: tuple[str, ...]
    status: AuditStatus
    attempts: int
    error_type: str | None = None


class MemoryAuditSink:
    def __init__(self) -> None:
        self._records: list[ToolAuditRecord] = []

    def record(
        self,
        *,
        execution_id: str,
        agent_id: str,
        tool_id: str,
        connector_ref: str,
        operation: str,
        argument_names: tuple[str, ...],
        status: AuditStatus,
        attempts: int,
        error_type: str | None = None,
    ) -> None:
        self._records.append(
            ToolAuditRecord(
                occurred_at=datetime.now(UTC),
                execution_id=execution_id,
                agent_id=agent_id,
                tool_id=tool_id,
                connector_ref=connector_ref,
                operation=operation,
                argument_names=argument_names,
                status=status,
                attempts=attempts,
                error_type=error_type,
            )
        )

    @property
    def records(self) -> tuple[ToolAuditRecord, ...]:
        return tuple(self._records)
