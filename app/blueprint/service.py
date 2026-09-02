"""Application service that composes loading, schema parsing, and validation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.blueprint.errors import BlueprintIssue, BlueprintLoadError, IssueSeverity
from app.blueprint.loader import BlueprintFormat, BlueprintLoader
from app.blueprint.schema import Blueprint
from app.blueprint.validator import BlueprintValidator


@dataclass(frozen=True, slots=True)
class BlueprintValidationResult:
    blueprint: Blueprint | None
    issues: tuple[BlueprintIssue, ...]

    @property
    def errors(self) -> tuple[BlueprintIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is IssueSeverity.ERROR)

    @property
    def warnings(self) -> tuple[BlueprintIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is IssueSeverity.WARNING)

    @property
    def is_valid(self) -> bool:
        return self.blueprint is not None and not self.errors


class BlueprintService:
    """Single entry point used by APIs, CLI commands, and the future Compiler."""

    def __init__(
        self,
        loader: BlueprintLoader | None = None,
        validator: BlueprintValidator | None = None,
    ) -> None:
        self._loader = loader or BlueprintLoader()
        self._validator = validator or BlueprintValidator()

    def validate_text(
        self,
        content: str,
        source_format: BlueprintFormat,
    ) -> BlueprintValidationResult:
        try:
            data = self._loader.load_text(content, source_format)
        except BlueprintLoadError as exc:
            return BlueprintValidationResult(None, (exc.issue,))
        return self.validate_data(data)

    def validate_path(self, path: Path) -> BlueprintValidationResult:
        try:
            data = self._loader.load_path(path)
        except BlueprintLoadError as exc:
            return BlueprintValidationResult(None, (exc.issue,))
        return self.validate_data(data)

    def validate_data(self, data: dict[str, Any]) -> BlueprintValidationResult:
        try:
            blueprint = Blueprint.model_validate(data)
        except ValidationError as exc:
            return BlueprintValidationResult(None, self._schema_issues(exc))

        issues = self._validator.validate(blueprint)
        return BlueprintValidationResult(blueprint, issues)

    @classmethod
    def _schema_issues(cls, error: ValidationError) -> tuple[BlueprintIssue, ...]:
        return tuple(
            BlueprintIssue(
                code=f"schema_{item['type']}",
                path=cls._format_location(item["loc"]),
                message=item["msg"],
            )
            for item in error.errors(include_url=False, include_input=False)
        )

    @staticmethod
    def _format_location(location: tuple[str | int, ...]) -> str:
        path = ""
        for part in location:
            if isinstance(part, int):
                path += f"[{part}]"
            elif path:
                path += f".{part}"
            else:
                path = str(part)
        return path or "$"
