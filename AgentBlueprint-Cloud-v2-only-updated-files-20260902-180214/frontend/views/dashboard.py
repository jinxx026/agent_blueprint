"""Enterprise console overview."""

import streamlit as st
from api_client import ApiClient, ApiError


def render(client: ApiClient) -> None:
    st.markdown(
        """
        <section class="hero">
          <div class="eyebrow">Enterprise AI Workspace</div>
          <h1>把企业 AI 从想法变成可治理的应用</h1>
          <p>选择业务模块、接入企业知识、配置多 Agent 流程，并通过权限、评测和审批后安全发布。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    try:
        session = client.get("/auth/session")
        modules = client.get("/control/modules")
        documents = client.get("/control/knowledge-documents")
        blueprints = client.get("/control/blueprints")
    except ApiError as exc:
        session, modules, documents, blueprints = {}, [], [], []
        st.error(f"后端连接失败：{exc}")

    columns = st.columns(4)
    columns[0].metric("已安装模块", sum(1 for item in modules if item.get("installed")))
    columns[1].metric("知识文档", len(documents))
    columns[2].metric("Blueprint", len(blueprints))
    columns[3].metric("当前组织", session.get("organization_id", "未连接"))

    st.markdown("### 产品运行链路")
    st.markdown(
        """
        <div class="pipeline">
          <div class="pipeline-step"><b>企业配置</b><span>模块、知识与连接器</span></div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step"><b>Blueprint</b><span>业务规则与 Agent 定义</span></div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step"><b>安全编译</b><span>生成确定性执行计划</span></div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step"><b>LangGraph</b><span>多 Agent 协作运行</span></div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step"><b>企业系统</b><span>ERP、CRM 与模型服务</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 核心能力")
    st.markdown(
        """
        <div class="feature-grid">
          <div class="feature-card"><b>模块化装配</b><br>
            按客服、合同、HR 等场景快速建立智能体。</div>
          <div class="feature-card"><b>企业级 RAG</b><br>
            上下文切片、混合召回、重排、压缩与引用。</div>
          <div class="feature-card"><b>安全执行</b><br>
            角色权限、工具网关、策略判断和人工审批。</div>
          <div class="feature-card"><b>质量门禁</b><br>
            用固定评测验证效果，通过后再发布环境。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
