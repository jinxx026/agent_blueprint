"""Shared UI helpers and presentation constants."""

from typing import Any

import streamlit as st
from api_client import ApiClient, ApiError


def load_or_warn(client: ApiClient, path: str, fallback: Any) -> Any:
    try:
        return client.get(path)
    except ApiError as exc:
        st.warning(str(exc))
        return fallback


def show_result(title: str, result: Any) -> None:
    st.success(title)
    with st.expander("查看后端返回结果", expanded=False):
        st.json(result)


def split_values(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]
