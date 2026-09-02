"""Compile orchestration declarations into framework-independent graph nodes and edges."""

from app.blueprint.schema import Blueprint, OrchestrationPattern
from app.compiler.diagnostics import CompilationDiagnostic, CompilationError
from app.compiler.intermediate import (
    GraphEdgeKind,
    GraphEdgeSpec,
    GraphNodeKind,
    GraphNodeSpec,
    GraphPlan,
)

START_NODE = "__start__"
END_NODE = "__end__"


class GraphPlanBuilder:
    def build(self, blueprint: Blueprint) -> GraphPlan:
        orchestration = blueprint.spec.orchestration
        nodes = tuple(
            GraphNodeSpec(id=agent.id, kind=GraphNodeKind.AGENT, agent_id=agent.id)
            for agent in blueprint.spec.agents
        )
        agents_by_id = {agent.id: agent for agent in blueprint.spec.agents}
        entry = agents_by_id[orchestration.entry_agent]

        if orchestration.pattern is OrchestrationPattern.CUSTOM:
            raise CompilationError(
                (
                    CompilationDiagnostic(
                        "custom_graph_not_supported",
                        "spec.orchestration.pattern",
                        "Custom graph compilation is not supported in ExecutionPlan v0.1",
                    ),
                )
            )

        edges = [
            GraphEdgeSpec(
                source=START_NODE,
                target=entry.id,
                kind=GraphEdgeKind.START,
                trigger="start",
            )
        ]

        if orchestration.pattern is OrchestrationPattern.SUPERVISOR:
            for delegate_id in entry.can_delegate_to:
                edges.append(
                    GraphEdgeSpec(
                        source=entry.id,
                        target=delegate_id,
                        kind=GraphEdgeKind.DELEGATE,
                        trigger=f"delegate:{delegate_id}",
                    )
                )
                edges.append(
                    GraphEdgeSpec(
                        source=delegate_id,
                        target=entry.id,
                        kind=GraphEdgeKind.RETURN,
                        trigger="subagent_completed",
                    )
                )
            edges.append(self._completion_edge(entry.id))
        elif orchestration.pattern is OrchestrationPattern.ROUTER:
            for delegate_id in entry.can_delegate_to:
                edges.append(
                    GraphEdgeSpec(
                        source=entry.id,
                        target=delegate_id,
                        kind=GraphEdgeKind.ROUTE,
                        trigger=f"route:{delegate_id}",
                    )
                )
                edges.append(self._completion_edge(delegate_id))
            edges.append(self._completion_edge(entry.id))
        elif orchestration.pattern is OrchestrationPattern.HANDOFF:
            for agent in blueprint.spec.agents:
                for delegate_id in agent.can_delegate_to:
                    edges.append(
                        GraphEdgeSpec(
                            source=agent.id,
                            target=delegate_id,
                            kind=GraphEdgeKind.HANDOFF,
                            trigger=f"handoff:{delegate_id}",
                        )
                    )
                edges.append(self._completion_edge(agent.id))
        else:
            edges.append(self._completion_edge(entry.id))

        return GraphPlan(
            pattern=orchestration.pattern,
            entry_node=entry.id,
            nodes=nodes,
            edges=tuple(edges),
            parallel_delegation=orchestration.parallel_delegation,
            human_in_the_loop=orchestration.human_in_the_loop,
        )

    @staticmethod
    def _completion_edge(source: str) -> GraphEdgeSpec:
        return GraphEdgeSpec(
            source=source,
            target=END_NODE,
            kind=GraphEdgeKind.COMPLETE,
            trigger="complete",
        )
