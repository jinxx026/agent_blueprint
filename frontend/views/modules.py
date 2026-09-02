"""Business module catalog and per-module RAG configuration."""

import streamlit as st
from api_client import ApiClient, ApiError

from views.common import load_or_warn, show_result, split_values


def render(client: ApiClient) -> None:
    st.title("业务模块与 RAG 定制")
    st.caption("每个业务模块拥有独立检索策略，避免所有部门共用一套粗糙参数。")
    modules = load_or_warn(client, "/control/modules", [])
    if not modules:
        st.info("后端连接后会显示客服、合同、HR、销售、财务和运营模块。")
        return

    selected_key = st.selectbox(
        "选择模块",
        [item["key"] for item in modules],
        format_func=lambda key: next(item["name"] for item in modules if item["key"] == key),
    )
    module = next(item for item in modules if item["key"] == selected_key)
    status = "已安装" if module.get("installed") else "未安装"
    st.subheader(f"{module['name']} · {status}")
    st.write(module["description"])
    a, b, c = st.columns(3)
    a.metric("Agent 数", module["agent_count"])
    b.metric("风险等级", module["risk_level"])
    c.metric("知识类型", len(module["knowledge_types"]))

    rag = module.get("rag") or {}
    with st.form(f"rag-{selected_key}"):
        left, right = st.columns(2)
        strategy = left.selectbox(
            "召回策略",
            ["hybrid", "semantic", "keyword"],
            index=["hybrid", "semantic", "keyword"].index(rag.get("strategy", "hybrid")),
        )
        chunk_strategy = right.selectbox(
            "切片策略",
            ["contextual", "structure", "fixed"],
            index=["contextual", "structure", "fixed"].index(
                rag.get("chunk_strategy", "contextual")
            ),
        )
        chunk_size = left.number_input("切片大小", 200, 4000, rag.get("chunk_size", 800), 100)
        chunk_overlap = right.number_input("切片重叠", 0, 1000, rag.get("chunk_overlap", 120), 20)
        candidate_count = left.number_input("初筛候选数", 5, 100, rag.get("candidate_count", 20))
        top_k = right.number_input("最终上下文数", 1, 20, rag.get("top_k", 5))
        rerank = left.checkbox("启用 rerank 重排", rag.get("rerank", True))
        compression = right.checkbox("启用上下文压缩", rag.get("compression", True))
        citations = left.checkbox("答案必须带引用", rag.get("return_citations", True))
        source_ids = st.text_input(
            "知识源 ID（逗号分隔；留空表示模块尚未绑定知识源）",
            ", ".join(rag.get("source_ids", [])),
        )
        saved = st.form_submit_button("安装并保存 RAG 配置", type="primary")
    if saved:
        payload = {
            "rag": {
                "strategy": strategy,
                "chunk_strategy": chunk_strategy,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "candidate_count": candidate_count,
                "top_k": top_k,
                "rerank": rerank,
                "compression": compression,
                "return_citations": citations,
                "source_ids": split_values(source_ids),
            }
        }
        try:
            show_result("模块配置已保存", client.put(f"/control/modules/{selected_key}", payload))
        except ApiError as exc:
            st.error(str(exc))

    if module.get("installed") and st.button("卸载此模块"):
        try:
            client.delete(f"/control/modules/{selected_key}")
            st.success("模块已卸载")
        except ApiError as exc:
            st.error(str(exc))
