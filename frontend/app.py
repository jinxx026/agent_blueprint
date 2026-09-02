"""AgentBlueprint Streamlit application entry point."""

import streamlit as st
from api_client import ApiClient, ApiError
from views import blueprints, dashboard, evaluations, knowledge, modules, security

st.set_page_config(
    page_title="AgentBlueprint 企业 AI 控制台",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: radial-gradient(circle at 80% 0%, #14213a 0, #090d17 38%); }
    [data-testid="stSidebar"] { background: #0d1320; border-right: 1px solid #273149; }
    [data-testid="stMetric"] {
      background: #111a2b; border: 1px solid #273149;
      padding: 1rem; border-radius: 14px;
    }
    .stButton > button { border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "api_base_url" not in st.session_state:
    st.session_state.api_base_url = "http://127.0.0.1:8000/api/v1"
if "access_token" not in st.session_state:
    st.session_state.access_token = ""

with st.sidebar:
    st.title("◈ AgentBlueprint")
    st.caption("Enterprise AI Studio · Streamlit MVP")
    page = st.radio(
        "功能",
        ["总览", "业务模块", "知识库", "Blueprint", "评测发布", "身份安全"],
        label_visibility="collapsed",
    )
    st.divider()
    with st.expander("后端连接", expanded=False):
        st.text_input("API 地址", key="api_base_url")
        st.text_input("访问令牌（开发模式可留空）", key="access_token", type="password")
        if st.button("检查连接"):
            try:
                health_client = ApiClient(
                    st.session_state.api_base_url, st.session_state.access_token
                )
                st.success(health_client.get("/health").get("status", "已连接"))
            except ApiError as exc:
                st.error(str(exc))

client = ApiClient(st.session_state.api_base_url, st.session_state.access_token)
pages = {
    "总览": dashboard.render,
    "业务模块": modules.render,
    "知识库": knowledge.render,
    "Blueprint": blueprints.render,
    "评测发布": evaluations.render,
    "身份安全": security.render,
}
pages[page](client)
