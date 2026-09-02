"""Shared state passed between nodes in a LangGraph execution."""

import operator
from typing import Annotated, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict


class AgentReport(BaseModel):
    """One specialist's immutable contribution to the final answer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: str
    content: str
    citations: tuple[str, ...] = ()
    tool_calls: tuple[str, ...] = ()
    tool_results: tuple[str, ...] = ()


class RuntimeState(TypedDict):
    """LangGraph state; list fields use reducers so node updates are appended."""

    question: str
    execution_id: str
    policy_context: dict[str, object]
    actor_roles: tuple[str, ...]
    pending_agents: list[str]
    reports: Annotated[list[AgentReport], operator.add]
    trace: Annotated[list[str], operator.add]
    model_calls: Annotated[int, operator.add]
    tool_calls: Annotated[int, operator.add]
    final_answer: NotRequired[str]
    next_node: NotRequired[str]
