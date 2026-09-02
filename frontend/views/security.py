"""Identity and enterprise security boundary page."""

import streamlit as st
from api_client import ApiClient

from views.common import load_or_warn


def render(client: ApiClient) -> None:
    st.title("身份与安全")
    st.caption("租户和角色由后端验证，不能由浏览器请求自行指定。")
    session = load_or_warn(client, "/auth/session", {})
    if session:
        left, right = st.columns(2)
        left.metric("组织", session.get("organization_id", "-"))
        right.metric("用户", session.get("subject", "-"))
        st.write("当前角色：", ", ".join(session.get("roles", [])))

    st.subheader("生产级安全边界")
    st.markdown(
        """
        - SSO/OIDC 确认用户身份，所有数据按组织隔离。
        - RAG 在召回前按组织、知识源和岗位权限过滤。
        - 工具调用统一经过 Tool Gateway、参数校验和审计。
        - 写操作和高风险动作由 Policy Engine 判断，必要时进入人工审批。
        - 模型密钥、数据库密码和连接器凭证只保存在服务端。
        """
    )
