"""Safe Blueprint source loader tests."""

import json

import pytest

from app.blueprint.errors import BlueprintLoadError
from app.blueprint.loader import BlueprintFormat, BlueprintLoader


def test_loader_reads_yaml_mapping() -> None:
    result = BlueprintLoader().load_text("kind: AgentBlueprint\n", BlueprintFormat.YAML)

    assert result == {"kind": "AgentBlueprint"}


def test_loader_reads_json_mapping() -> None:
    content = json.dumps({"kind": "AgentBlueprint"})

    result = BlueprintLoader().load_text(content, BlueprintFormat.JSON)

    assert result == {"kind": "AgentBlueprint"}


@pytest.mark.parametrize(
    ("content", "source_format"),
    [
        ("kind: one\nkind: two\n", BlueprintFormat.YAML),
        ('{"kind":"one","kind":"two"}', BlueprintFormat.JSON),
    ],
)
def test_loader_rejects_duplicate_keys(content: str, source_format: BlueprintFormat) -> None:
    with pytest.raises(BlueprintLoadError) as exc_info:
        BlueprintLoader().load_text(content, source_format)

    assert exc_info.value.issue.code == "parse_error"


def test_loader_rejects_unsafe_yaml_tags() -> None:
    content = "value: !!python/object/apply:os.system ['echo unsafe']"

    with pytest.raises(BlueprintLoadError) as exc_info:
        BlueprintLoader().load_text(content, BlueprintFormat.YAML)

    assert exc_info.value.issue.code == "parse_error"


def test_loader_requires_mapping_root() -> None:
    with pytest.raises(BlueprintLoadError) as exc_info:
        BlueprintLoader().load_text("- one\n- two\n", BlueprintFormat.YAML)

    assert exc_info.value.issue.code == "root_must_be_object"
