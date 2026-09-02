"""Enterprise console overview."""

import streamlit as st
from api_client import ApiClient

from views.common import load_or_warn


def render(client: ApiClient) -> None:
    st.title("企业 AI 控制台")
    st.caption("从业务配置到安全发布，把企业智能体做成一条可管理的生产线。")

    session = load_or_warn(client, "/auth/session", {})
    modules = load_or_warn(client, "/control/modules", [])
    documents = load_or_warn(client, "/control/knowledge-documents", [])
    blueprints = load_or_warn(client, "/control/blueprints", [])

    columns = st.columns(4)
    columns[0].metric("已安装模块", sum(1 for item in modules if item.get("installed")))
    columns[1].metric("知识文档", len(documents))
    columns[2].metric("Blueprint", len(blueprints))
    columns[3].metric("当前组织", session.get("organization_id", "未连接"))

    st.subheader("产品运行链路")
    st.graphviz_chart(
        """
        digraph platform {
          rankdir=LR; bgcolor="transparent";
          node [shape=box, style="rounded,filled", fillcolor="#172033"];
          node [color="#46516b", fontcolor="#e7ecf7"];
          edge [color="#687594"];
          console [label="企业控制台"];
          compiler [label="Blueprint\nCompiler"];
          plan [label="安全执行计划"];
          runtime [label="LangGraph\nRuntime"];
          systems [label="ERP / CRM /\n模型与数据库"];
          console -> compiler -> plan -> runtime -> systems;
        }
        """,
        width="stretch",
    )

    st.subheader("现在可以完成什么")
    st.markdown(
        """
        1. 在 **业务模块** 选择企业场景，并单独配置上下文切片、召回、rerank 和压缩。
        2. 在 **知识库** 导入企业文本，并限制哪些岗位可以检索。
        3. 在 **Blueprint** 定义 Agent、工具、审批和运行边界，然后校验和编译。
        4. 在 **评测发布** 用固定测试用例把关，通过后再发布测试或生产版本。
        """
    )
