"""Provider-neutral model boundary plus a deterministic local implementation."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.compiler.intermediate import AgentSpec, ToolBindingSpec
from app.runtime.state import AgentReport


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_id: str
    arguments: dict[str, object]


class AgentPrompt(BaseModel):
    """Everything a model may see for one agent call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent: AgentSpec
    question: str
    context_chunks: tuple[str, ...]
    prior_reports: tuple[AgentReport, ...]
    available_tools: tuple[ToolBindingSpec, ...]


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str
    tool_requests: tuple[ToolRequest, ...] = ()


class AgentModel(Protocol):
    """Small interface implemented later by OpenAI, Azure, or local models."""

    def invoke(self, prompt: AgentPrompt) -> AgentResponse: ...


class DeterministicAgentModel:
    """Offline model substitute used for development and repeatable tests."""

    def invoke(self, prompt: AgentPrompt) -> AgentResponse:
        if prompt.prior_reports:
            joined = "\n".join(f"- {report.content}" for report in prompt.prior_reports)
            return AgentResponse(content=f"已由{prompt.agent.display_name}汇总：\n{joined}")

        context = "；".join(prompt.context_chunks) or "未配置可用知识"
        return AgentResponse(
            content=f"{prompt.agent.display_name}针对“{prompt.question}”的处理结果：{context}"
        )
