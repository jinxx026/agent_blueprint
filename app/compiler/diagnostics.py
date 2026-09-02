"""Compiler-specific diagnostics and failure type."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompilationDiagnostic:
    code: str
    path: str
    message: str


class CompilationError(ValueError):
    """Raised when a validated execution plan cannot be produced."""

    def __init__(self, diagnostics: tuple[CompilationDiagnostic, ...]) -> None:
        self.diagnostics = diagnostics
        message = "; ".join(item.message for item in diagnostics)
        super().__init__(message)
