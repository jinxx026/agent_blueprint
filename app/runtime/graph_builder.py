"""Translate an ExecutionPlan into an executable LangGraph state machine."""

from collections.abc import Mapping
from typing import Any

from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph

from app.compiler.intermediate import ExecutionPlan, OrchestrationPattern
from app.runtime.agent_factory import AgentInvocation
from app.runtime.state import AgentReport, RuntimeState


class RuntimeGraphBuilder:
    """Build the outer multi-agent graph; each node is a LangChain Runnable."""

    def build(
        self,
        plan: ExecutionPlan,
        agents: Mapping[str, Runnable[AgentInvocation, AgentReport]],
        checkpointer: Any,
    ) -> Any:
        graph = StateGraph(RuntimeState)
        entry_id = plan.graph.entry_node
        entry_runnable = agents[entry_id]
        worker_ids = self._worker_ids(plan)

        def coordinator(state: RuntimeState) -> dict[str, object]:
            pending = state["pending_agents"]
            if pending:
                target = pending[0]
                return {
                    "pending_agents": pending[1:],
                    "next_node": target,
                    "trace": [f"{entry_id}:delegate:{target}"],
                }

            report = entry_runnable.invoke(
                AgentInvocation(
                    question=state["question"],
                    prior_reports=tuple(state["reports"]),
                    execution_id=state["execution_id"],
                    policy_context=state["policy_context"],
                    actor_roles=state["actor_roles"],
                )
            )
            return {
                "final_answer": report.content,
                "next_node": END,
                "trace": [f"{entry_id}:complete"],
                "model_calls": 1,
                "tool_calls": len(report.tool_results),
            }

        graph.add_node(entry_id, coordinator)

        for worker_id in worker_ids:
            runnable = agents[worker_id]

            def worker(
                state: RuntimeState,
                runnable: Runnable[AgentInvocation, AgentReport] = runnable,
                worker_id: str = worker_id,
            ) -> dict[str, object]:
                report = runnable.invoke(
                    AgentInvocation(
                        question=state["question"],
                        execution_id=state["execution_id"],
                        policy_context=state["policy_context"],
                        actor_roles=state["actor_roles"],
                    )
                )
                return {
                    "reports": [report],
                    "trace": [f"{worker_id}:complete"],
                    "model_calls": 1,
                    "tool_calls": len(report.tool_results),
                }

            graph.add_node(worker_id, worker)
            graph.add_edge(worker_id, entry_id)

        destinations = {worker_id: worker_id for worker_id in worker_ids}
        destinations[END] = END
        graph.add_edge(START, entry_id)
        graph.add_conditional_edges(
            entry_id,
            lambda state: state["next_node"],
            destinations,
        )
        return graph.compile(checkpointer=checkpointer)

    @staticmethod
    def initial_workers(plan: ExecutionPlan) -> list[str]:
        entry = next(agent for agent in plan.agents if agent.id == plan.graph.entry_node)
        if plan.graph.pattern is OrchestrationPattern.SINGLE:
            return []
        if plan.graph.pattern is OrchestrationPattern.ROUTER:
            return list(entry.delegate_to[:1])
        return list(entry.delegate_to)

    @classmethod
    def _worker_ids(cls, plan: ExecutionPlan) -> tuple[str, ...]:
        return tuple(cls.initial_workers(plan))
