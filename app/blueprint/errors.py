"""Stable error vocabulary shared by Blueprint loading, validation, and APIs."""

from dataclasses import dataclass
from enum import StrEnum


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class BlueprintIssue:
    """One machine-readable problem tied to a Blueprint path."""

    code: str
    path: str
    message: str
    severity: IssueSeverity = IssueSeverity.ERROR


class BlueprintLoadError(ValueError):
    """Raised when source text cannot become a top-level mapping."""

    def __init__(self, issue: BlueprintIssue) -> None:
        super().__init__(issue.message)
        self.issue = issue
