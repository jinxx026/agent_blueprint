"""Compile Blueprint RAG assignments into portable Retriever specifications."""

from app.blueprint.schema import Blueprint
from app.compiler.intermediate import RetrieverSpec


class RetrieverPlanBuilder:
    def build(self, blueprint: Blueprint) -> tuple[RetrieverSpec, ...]:
        if not blueprint.spec.rag.enabled:
            return ()

        rag = blueprint.spec.rag
        return tuple(
            RetrieverSpec(
                id=f"retriever-{agent.id}",
                agent_id=agent.id,
                strategy=rag.strategy,
                source_ids=tuple(agent.knowledge),
                top_k=rag.default_top_k,
                rerank=rag.rerank,
                return_citations=rag.return_citations,
            )
            for agent in blueprint.spec.agents
            if agent.knowledge
        )
