"""Controlled tool execution boundary used by LangChain agents."""

import json
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


def create_demo_tool_registry() -> MemoryToolRegistry:
    """Safe local connectors used by the zero-configuration product walkthrough."""

    def identity(arguments: Mapping[str, Any]) -> str:
        return json.dumps(
            {"verified": True, "order_id": arguments.get("order_id")}, ensure_ascii=False
        )

    def order(arguments: Mapping[str, Any]) -> str:
        return json.dumps(
            {"order_id": arguments.get("order_id"), "status": "delivered", "paid_amount": 299},
            ensure_ascii=False,
        )

    def refund(arguments: Mapping[str, Any]) -> str:
        return json.dumps(
            {"draft_id": "REFUND-DEMO-001", "status": "draft_created", **dict(arguments)},
            ensure_ascii=False,
        )

    return MemoryToolRegistry(
        {
            "verify_customer_identity": identity,
            "get_order": order,
            "create_refund_draft": refund,
        }
    )
