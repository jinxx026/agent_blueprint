from app.rag import ContextualChunker, RagDocument


def test_contextual_chunking_keeps_structure_summary_and_neighbors() -> None:
    document = RagDocument(
        tenant_id="tenant-a",
        source_id="policy",
        document_id="refund-v1",
        title="售后政策",
        content=(
            "# 退款条件\n普通商品签收后七天内可以退款。需要提供订单号和购买凭证。"
            "商品必须保持完好，不影响二次销售。\n"
            "## 特殊商品\n定制商品和已激活软件不支持无理由退款。"
        ),
        allowed_roles=("customer_service",),
        citation_base="policy://refund-v1",
    )

    chunks = ContextualChunker(chunk_size=45, chunk_overlap=8).split(document)

    assert len(chunks) >= 2
    assert all("[文档: 售后政策]" in chunk.contextual_content for chunk in chunks)
    assert any("[章节: 退款条件]" in chunk.contextual_content for chunk in chunks)
    assert any("[相邻内容:" in chunk.contextual_content for chunk in chunks)
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert all(chunk.citation.startswith("policy://refund-v1#chunk=") for chunk in chunks)
