"""Safe, format-aware Blueprint source loading."""

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

from app.blueprint.errors import BlueprintIssue, BlueprintLoadError

MAX_BLUEPRINT_BYTES = 1_048_576


class BlueprintFormat(StrEnum):
    YAML = "yaml"
    JSON = "json"

    @classmethod
    def from_path(cls, path: Path) -> "BlueprintFormat":
        suffix = path.suffix.lower()
        if suffix in {".yaml", ".yml"}:
            return cls.YAML
        if suffix == ".json":
            return cls.JSON
        raise BlueprintLoadError(
            BlueprintIssue(
                code="unsupported_format",
                path="$",
                message=f"Unsupported Blueprint file extension: {suffix or '<none>'}",
            )
        )


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """SafeLoader variant that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _json_object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"found duplicate key {key!r}")
        result[key] = value
    return result


class BlueprintLoader:
    """Parse trusted file content or untrusted API text without executing code."""

    def load_text(self, content: str, source_format: BlueprintFormat) -> dict[str, Any]:
        if not content.strip():
            raise BlueprintLoadError(
                BlueprintIssue("empty_document", "$", "Blueprint content must not be empty")
            )
        if len(content.encode("utf-8")) > MAX_BLUEPRINT_BYTES:
            raise BlueprintLoadError(
                BlueprintIssue(
                    "document_too_large",
                    "$",
                    f"Blueprint exceeds the {MAX_BLUEPRINT_BYTES} byte limit",
                )
            )

        try:
            if source_format is BlueprintFormat.YAML:
                parsed = yaml.load(content, Loader=_UniqueKeySafeLoader)
            else:
                parsed = json.loads(content, object_pairs_hook=_json_object_without_duplicates)
        except (json.JSONDecodeError, yaml.YAMLError, TypeError, ValueError) as exc:
            raise BlueprintLoadError(
                BlueprintIssue("parse_error", "$", f"Blueprint cannot be parsed: {exc}")
            ) from exc

        if not isinstance(parsed, dict):
            raise BlueprintLoadError(
                BlueprintIssue(
                    "root_must_be_object",
                    "$",
                    "Blueprint root must be a YAML mapping or JSON object",
                )
            )
        return parsed

    def load_path(self, path: Path) -> dict[str, Any]:
        """Load an internal, trusted path; public APIs must call ``load_text``."""

        source_format = BlueprintFormat.from_path(path)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise BlueprintLoadError(
                BlueprintIssue("file_read_error", "$", f"Cannot read Blueprint: {exc}")
            ) from exc
        return self.load_text(content, source_format)
