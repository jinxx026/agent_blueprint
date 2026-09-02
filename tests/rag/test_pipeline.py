from pathlib import Path

from app.blueprint.loader import BlueprintFormat
from app.blueprint.service import BlueprintService
from app.compiler import BlueprintCompiler
from app.rag import (
    ContextCompressor,
    ContextualChunker,
    HashEmbeddings,
    LocalCrossEncoderReranker,
    MemoryHybridIndex,
    RagDocument,
    RagKnowledgeStore,
    RagPipeline,
)
from app.runtime import BlueprintExecutor


def make_pipeline() -> RagPipeline:
    return RagPipeline(
        ContextualChunker(chunk_size=120, chunk_overlap=20),
        MemoryHybridIndex(HashEmbeddings()),
        LocalCrossEncoderReranker(),
        ContextCompressor(max_characters_per_chunk=80),
    )


def documents() -> list[RagDocument]:
    return [
        RagDocument(
            tenant_id="tenant-a",
            source_id="after_sales_policy",
            document_id="refund-policy",
            title="退款政策",
            content=(
                "# 公司历史\n公司成立于2010年，总部位于上海。这段内容与退款条件无关。\n"
                "# 退款条件\n普通商品签收七天内可以申请退款。退款需要订单号和购买凭证。"
                "超过七天需要人工审核。"
            ),
            allowed_roles=("customer_service", "supervisor"),
            citation_base="kb://tenant-a/refund-policy",
        ),
        RagDocument(
            tenant_id="tenant-a",
            source_id="after_sales_policy",
            document_id="finance-only",
            title="财务内部退款规则",
            content="# 退款条件\n所有退款都需要查看银行账户密码。",
            allowed_roles=("finance",),
            citation_base="kb://tenant-a/finance-only",
        ),
        RagDocument(
            tenant_id="tenant-b",
            source_id="after_sales_policy",
            document_id="other-tenant",
            title="其他企业政策",
            content="# 退款条件\n退款不需要任何条件，可以立即办理。",
            allowed_roles=("customer_service",),
            citation_base="kb://tenant-b/other",
        ),
    ]


def test_pipeline_reranks_compresses_and_enforces_tenant_role_filters() -> None:
    pipeline = make_pipeline()
    assert pipeline.ingest(documents()) >= 3

    results = pipeline.retrieve(
        "普通商品退款需要什么条件？",
        tenant_id="tenant-a",
        roles=frozenset({"customer_service"}),
        source_ids=frozenset({"after_sales_policy"}),
        top_k=2,
        rerank=True,
    )

    assert results
    assert "七天内" in results[0].content
    assert "订单号" in results[0].content
    assert results[0].rerank_score >= results[-1].rerank_score
    assert results[0].compressed_characters < results[0].original_characters
    assert all("finance-only" not in result.citation for result in results)
    assert all("tenant-b" not in result.citation for result in results)


def test_rag_pipeline_supplies_compressed_citations_to_multi_agent_runtime(
    example_blueprint_path: Path,
) -> None:
    validation = BlueprintService().validate_text(
        example_blueprint_path.read_text(encoding="utf-8"), BlueprintFormat.YAML
    )
    assert validation.blueprint is not None
    plan = BlueprintCompiler().compile(validation.blueprint)
    pipeline = make_pipeline()
    pipeline.ingest(documents())
    store = RagKnowledgeStore(pipeline, tenant_id="tenant-a", roles=frozenset({"customer_service"}))

    result = BlueprintExecutor(knowledge=store).execute(
        plan, "普通商品退款需要什么条件？", "rag-runtime-test"
    )

    assert result.citations
    assert all(citation.startswith("kb://tenant-a/") for citation in result.citations)
    assert "订单号" in result.answer


def test_reingesting_a_document_replaces_stale_chunks() -> None:
    pipeline = make_pipeline()
    original = documents()[0]
    pipeline.ingest([original])
    updated = original.model_copy(
        update={
            "content": "# 新政策\n普通商品退款期限调整为三十天。",
            "citation_base": "kb://tenant-a/refund-policy-v2",
        }
    )
    pipeline.ingest([updated])

    results = pipeline.retrieve(
        "普通商品退款期限",
        tenant_id="tenant-a",
        roles=frozenset({"customer_service"}),
        source_ids=frozenset({"after_sales_policy"}),
        top_k=10,
    )

    assert results
    assert all("refund-policy-v2" in result.citation for result in results)
    assert all("七天内" not in result.content for result in results)
