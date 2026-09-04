"""Provider-neutral model boundary plus a deterministic local implementation."""

import re
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

        tool_ids = {tool.id for tool in prompt.available_tools}
        requests_refund = "退款" in prompt.question and any(
            action in prompt.question for action in ("创建", "发起", "申请")
        )
        if "create_refund_draft" in tool_ids and requests_refund:
            order_match = re.search(
                r"(?:订单(?:号)?[：:\s]*)?([A-Za-z][A-Za-z0-9-]{2,})", prompt.question
            )
            amount_match = re.search(r"(\d+(?:\.\d{1,2})?)\s*元", prompt.question)
            order_id = order_match.group(1) if order_match else "DEMO-ORDER-001"
            amount = float(amount_match.group(1)) if amount_match else 100.0
            return AgentResponse(
                content="已核对退款请求，准备创建退款草稿并提交主管审批。",
                tool_requests=(
                    ToolRequest(
                        tool_id="create_refund_draft",
                        arguments={
                            "order_id": order_id,
                            "amount": amount,
                            "reason": "客户依据售后政策申请退款",
                        },
                    ),
                ),
            )

        context = "；".join(prompt.context_chunks) or "未配置可用知识"
        return AgentResponse(
            content=f"{prompt.agent.display_name}针对“{prompt.question}”的处理结果：{context}"
        )
