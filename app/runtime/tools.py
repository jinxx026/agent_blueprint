"""Controlled tool execution boundary used by LangChain agents."""

from collections.abc import Callable, Mapping
from typing import Any

from app.compiler.intermediate import ToolBindingSpec

ToolHandler = Callable[[Mapping[str, Any]], object]


class ToolNotRegisteredError(RuntimeError):
    pass


class MemoryToolRegistry:
    """Maps Blueprint tool IDs to safe callables; real connectors arrive next phase."""

    def __init__(self, handlers: Mapping[str, ToolHandler] | None = None) -> None:
        self._handlers = dict(handlers or {})

    def execute(
        self,
        spec: ToolBindingSpec,
        arguments: Mapping[str, Any],
        *,
        agent_id: str = "unknown-agent",
        execution_id: str = "unknown-execution",
        policy_context: Mapping[str, Any] | None = None,
        actor_roles: tuple[str, ...] = (),
    ) -> str:
        handler = self._handlers.get(spec.id)
        if handler is None:
            raise ToolNotRegisteredError(f"Tool '{spec.id}' has no registered connector")
        return str(handler(arguments))
