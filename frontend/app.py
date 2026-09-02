"""AgentBlueprint Streamlit application entry point."""

import streamlit as st
from api_client import ApiClient, ApiError
from streamlit.errors import StreamlitSecretNotFoundError
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
    :root { --ink: #182033; --muted: #657089; --line: #e5e9f2; --brand: #5b5bd6; }
    .stApp { background: #f6f7fb; color: var(--ink); }
    .block-container { max-width: 1320px; padding: 2.4rem 3rem 5rem; }
    header[data-testid="stHeader"] { background: rgba(246, 247, 251, .92); }
    [data-testid="stSidebar"] {
      background: #ffffff; border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] .block-container { padding: 2rem 1.15rem; }
    [data-testid="stSidebar"] [role="radiogroup"] { gap: .35rem; }
    [data-testid="stSidebar"] [role="radiogroup"] label {
      padding: .7rem .8rem; border-radius: 10px; transition: .15s ease;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #f2f3ff; }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
      background: #ededff; color: #4545b8;
    }
    h1, h2, h3 { color: var(--ink); letter-spacing: -.025em; }
    p, .stCaption { color: var(--muted); }
    [data-testid="stMetric"] {
      background: #ffffff; border: 1px solid var(--line); padding: 1.1rem 1.2rem;
      border-radius: 14px; box-shadow: 0 8px 24px rgba(28, 39, 66, .04);
    }
    .stButton > button { border-radius: 9px; min-height: 2.55rem; font-weight: 600; }
    .stButton > button[kind="primary"] { box-shadow: 0 7px 18px rgba(91, 91, 214, .2); }
    .brand { display:flex; align-items:center; gap:.7rem; margin: .15rem 0 .2rem; }
    .brand-mark { width:34px; height:34px; border-radius:10px; background:#5b5bd6;
      color:white; display:grid; place-items:center; font-weight:800; }
    .brand-name { font-size:1.05rem; font-weight:750; color:#151c2f; }
    .brand-sub { color:#8790a5; font-size:.76rem; margin:0 0 1.5rem 2.95rem; }
    .mode-pill { display:inline-flex; align-items:center; gap:.45rem; padding:.38rem .65rem;
      border:1px solid #dfe3ed; background:#fafbfe; border-radius:999px; color:#59647c;
      font-size:.78rem; margin-top:.8rem; }
    .mode-dot { width:7px; height:7px; border-radius:50%; background:#37b47e; }
    .hero { background:linear-gradient(125deg,#ffffff 10%,#f0f1ff 100%);
      border:1px solid #e2e5f2; border-radius:20px; padding:2rem 2.2rem; margin-bottom:1.3rem;
      box-shadow:0 16px 40px rgba(39,45,90,.06); }
    .eyebrow { color:#5b5bd6; font-weight:750; font-size:.78rem; letter-spacing:.08em;
      text-transform:uppercase; margin-bottom:.65rem; }
    .hero h1 { font-size:2.25rem; margin:.1rem 0 .65rem; }
    .hero p { font-size:1rem; max-width:720px; margin:0; line-height:1.75; }
    .pipeline { display:flex; align-items:center; gap:.65rem; margin:1rem 0 2rem; }
    .pipeline-step { flex:1; background:white; border:1px solid var(--line); border-radius:13px;
      padding:1rem; min-height:78px; box-shadow:0 6px 20px rgba(28,39,66,.035); }
    .pipeline-step b { display:block; color:#202941; margin-bottom:.25rem; }
    .pipeline-step span { color:#7a849a; font-size:.78rem; }
    .pipeline-arrow { color:#9aa3b6; font-size:1.2rem; }
    .feature-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8rem; }
    .feature-card { background:white; border:1px solid var(--line); border-radius:13px;
      padding:1rem 1.1rem; color:#35405a; }
    .feature-card b { color:#202941; }
    @media (max-width: 900px) {
      .block-container { padding:1.3rem 1rem 3rem; }
      .pipeline { display:grid; grid-template-columns:1fr; }
      .pipeline-arrow { transform:rotate(90deg); text-align:center; }
      .feature-grid { grid-template-columns:1fr; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

legacy_local_urls = {
    "http://127.0.0.1:8000/api/v1",
    "http://localhost:8000/api/v1",
}
if "api_base_url" not in st.session_state or st.session_state.api_base_url in legacy_local_urls:
    try:
        default_api_base_url = str(st.secrets["API_BASE_URL"])
    except (KeyError, StreamlitSecretNotFoundError):
        default_api_base_url = "embedded"
    st.session_state.api_base_url = default_api_base_url
if "access_token" not in st.session_state:
    st.session_state.access_token = ""

client = ApiClient(st.session_state.api_base_url, st.session_state.access_token)

with st.sidebar:
    st.markdown(
        """
        <div class="brand"><div class="brand-mark">A</div>
        <div class="brand-name">AgentBlueprint</div></div>
        <div class="brand-sub">企业智能体装配平台 · Cloud v2</div>
        """,
        unsafe_allow_html=True,
    )
    page = st.radio(
        "功能",
        ["总览", "业务模块", "知识库", "Blueprint", "评测发布", "身份安全"],
        label_visibility="collapsed",
    )
    st.divider()
    mode_label = "内置演示后端" if client.is_embedded else "独立企业后端"
    st.markdown(
        f'<div class="mode-pill"><span class="mode-dot"></span>{mode_label}</div>',
        unsafe_allow_html=True,
    )
    if client.is_embedded:
        st.caption("云端可直接体验；重启后演示数据可能重置。")
    with st.expander("后端连接", expanded=False):
        st.text_input(
            "API 地址",
            key="api_base_url",
            help="输入 embedded 使用内置演示后端，或填写独立后端的 HTTPS /api/v1 地址。",
        )
        st.text_input("访问令牌（开发模式可留空）", key="access_token", type="password")
        if st.button("检查连接"):
            try:
                health_client = ApiClient(
                    st.session_state.api_base_url, st.session_state.access_token
                )
                st.success(health_client.get("/health").get("status", "已连接"))
            except ApiError as exc:
                st.error(str(exc))

pages = {
    "总览": dashboard.render,
    "业务模块": modules.render,
    "知识库": knowledge.render,
    "Blueprint": blueprints.render,
    "评测发布": evaluations.render,
    "身份安全": security.render,
}
pages[page](client)
