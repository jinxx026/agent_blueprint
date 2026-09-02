"""Build least-privilege LangChain runnables for compiled agents."""

from dataclasses import dataclass

from langchain_core.runnables import Runnable, RunnableLambda

from app.compiler.intermediate import AgentSpec, ExecutionPlan, RetrieverSpec, ToolBindingSpec
from app.runtime.model import AgentModel, AgentPrompt
from app.runtime.retrievers import KnowledgeDocument, KnowledgeRetriever
from app.runtime.state import AgentReport
from app.tooling import ToolExecutor


@dataclass(frozen=True)
class AgentInvocation:
    question: str
    prior_reports: tuple[AgentReport, ...] = ()
    execution_id: str = "unknown-execution"
    policy_context: dict[str, object] | None = None
    actor_roles: tuple[str, ...] = ()


class AgentFactory:
    """Turns portable AgentSpecs into LangChain Runnable objects."""

    def __init__(
        self,
        plan: ExecutionPlan,
        model: AgentModel,
        knowledge: KnowledgeRetriever,
        tools: ToolExecutor,
    ) -> None:
        self._plan = plan
        self._model = model
        self._knowledge = knowledge
        self._tools = tools

    def build(self, agent: AgentSpec) -> Runnable[AgentInvocation, AgentReport]:
        retriever = next(
            (item for item in self._plan.retrievers if item.agent_id == agent.id), None
        )
        allowed_tools = tuple(tool for tool in self._plan.tools if tool.id in agent.tool_ids)

        def run(invocation: AgentInvocation) -> AgentReport:
            documents = self._retrieve(retriever, invocation.question)
            response = self._model.invoke(
                AgentPrompt(
                    agent=agent,
                    question=invocation.question,
                    context_chunks=tuple(document.content for document in documents),
                    prior_reports=invocation.prior_reports,
                    available_tools=allowed_tools,
                )
            )
            tools_by_id: dict[str, ToolBindingSpec] = {tool.id: tool for tool in allowed_tools}
            tool_results = []
            for request in response.tool_requests:
                if request.tool_id not in tools_by_id:
                    raise PermissionError(
                        f"Agent '{agent.id}' cannot call tool '{request.tool_id}'"
                    )
                tool_results.append(
                    self._tools.execute(
                        tools_by_id[request.tool_id],
                        request.arguments,
                        agent_id=agent.id,
                        execution_id=invocation.execution_id,
                        policy_context=invocation.policy_context,
                        actor_roles=invocation.actor_roles,
                    )
                )
            return AgentReport(
                agent_id=agent.id,
                content=response.content,
                citations=tuple(document.citation for document in documents),
                tool_calls=tuple(request.tool_id for request in response.tool_requests),
                tool_results=tuple(tool_results),
            )

        return RunnableLambda(run).with_config({"run_name": f"agent:{agent.id}"})

    def _retrieve(self, spec: RetrieverSpec | None, question: str) -> tuple[KnowledgeDocument, ...]:
        if spec is None:
            return ()
        return self._knowledge.retrieve(spec, question)
