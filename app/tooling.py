"""Lowest-level tool execution contract shared by runtime and governance."""

from collections.abc import Mapping
from typing import Any, Protocol

from app.compiler.intermediate import ToolBindingSpec


class ToolExecutor(Protocol):
    def execute(
        self,
        spec: ToolBindingSpec,
        arguments: Mapping[str, Any],
        *,
        agent_id: str = "unknown-agent",
        execution_id: str = "unknown-execution",
        policy_context: Mapping[str, Any] | None = None,
        actor_roles: tuple[str, ...] = (),
    ) -> str: ...
