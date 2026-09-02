"""Blueprint Pydantic schema and service tests."""

from pathlib import Path

from app.blueprint.schema import OrchestrationPattern, RagStrategy
from app.blueprint.service import BlueprintService


def test_example_blueprint_is_valid(example_blueprint_path: Path) -> None:
    result = BlueprintService().validate_path(example_blueprint_path)

    assert result.is_valid is True
    assert result.errors == ()
    assert result.blueprint is not None
    assert result.blueprint.metadata.name == "customer-refund-assistant"
    assert result.blueprint.spec.rag.strategy is RagStrategy.AGENTIC
    assert result.blueprint.spec.orchestration.pattern is OrchestrationPattern.SUPERVISOR
    assert len(result.blueprint.spec.agents) == 4


def test_schema_rejects_unknown_field(example_blueprint_data: dict[str, object]) -> None:
    example_blueprint_data["unexpected"] = True

    result = BlueprintService().validate_data(example_blueprint_data)

    assert result.is_valid is False
    assert result.blueprint is None
    assert any(issue.path == "unexpected" for issue in result.errors)
