"""Knowledge ingestion and access-boundary page."""

import streamlit as st
from api_client import ApiClient, ApiError

from views.common import load_or_warn, show_result, split_values


def render(client: ApiClient) -> None:
    st.title("企业知识库")
    st.caption("当前版本先支持安全的文本导入；文件解析、定时同步和对象存储属于生产扩展。")

    with st.form("knowledge-document", clear_on_submit=True):
        left, right = st.columns(2)
        source_id = left.text_input("知识源 ID", placeholder="after-sales-policy")
        title = right.text_input("文档标题", placeholder="2026 售后退款政策")
        roles = left.text_input("允许角色（逗号分隔）", value="customer_service, supervisor")
        citation_base = right.text_input("引用前缀", value="knowledge://customer-service/policy")
        content = st.text_area("文档正文", height=220, placeholder="粘贴企业制度、SOP 或产品资料……")
        submitted = st.form_submit_button("导入知识库", type="primary")
    if submitted:
        try:
            result = client.post(
                "/control/knowledge-documents",
                {
                    "source_id": source_id,
                    "title": title,
                    "content": content,
                    "allowed_roles": split_values(roles),
                    "citation_base": citation_base,
                },
            )
            show_result("文档已导入，并绑定组织与角色权限", result)
        except ApiError as exc:
            st.error(str(exc))

    st.subheader("已导入文档")
    documents = load_or_warn(client, "/control/knowledge-documents", [])
    if not documents:
        st.info("还没有文档。先导入一份企业制度或业务 SOP。")
    for item in documents:
        with st.expander(f"{item['title']} · v{item['version']}"):
            st.caption(f"来源：{item['source_id']} · 角色：{', '.join(item['allowed_roles'])}")
            st.write(item["content"][:1000])
