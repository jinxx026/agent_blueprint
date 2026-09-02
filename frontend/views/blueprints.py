"""Blueprint authoring, validation and compilation page."""

from pathlib import Path

import streamlit as st
from api_client import ApiClient, ApiError

from views.common import load_or_warn, show_result

EXAMPLE_PATH = (
    Path(__file__).resolve().parents[2] / "examples" / "customer-support" / "blueprint.yaml"
)


def render(client: ApiClient) -> None:
    st.title("Blueprint 设计与编译")
    st.caption("Blueprint 是企业填写的配置；编译器把它变成可审计的安全执行计划。")
    if "blueprint_content" not in st.session_state:
        st.session_state.blueprint_content = EXAMPLE_PATH.read_text(encoding="utf-8")

    content = st.text_area(
        "YAML Blueprint",
        key="blueprint_content",
        height=520,
        label_visibility="collapsed",
    )
    validate_col, compile_col, save_col = st.columns(3)
    try:
        if validate_col.button("1. 校验", width="stretch"):
            show_result(
                "校验完成",
                client.post("/blueprints/validate", {"content": content, "format": "yaml"}),
            )
        if compile_col.button("2. 编译执行计划", width="stretch"):
            show_result(
                "编译完成",
                client.post("/blueprints/compile", {"content": content, "format": "yaml"}),
            )
        if save_col.button("3. 保存版本", type="primary", width="stretch"):
            show_result(
                "Blueprint 已保存",
                client.post("/control/blueprints", {"content": content, "format": "yaml"}),
            )
    except ApiError as exc:
        st.error(str(exc))

    st.subheader("组织内 Blueprint")
    records = load_or_warn(client, "/control/blueprints", [])
    for record in records:
        st.write(f"**{record['display_name']}** · {record['version']} · {record['stage']}")
