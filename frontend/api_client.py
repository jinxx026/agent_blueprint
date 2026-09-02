"""Small HTTP client used by every Streamlit page."""

from dataclasses import dataclass
from typing import Any

import httpx


class ApiError(RuntimeError):
    """A readable backend error that can be shown directly in the UI."""


@dataclass(frozen=True)
class ApiClient:
    base_url: str
    token: str = ""

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = {"Accept": "application/json"}
        if self.token.strip():
            headers["Authorization"] = f"Bearer {self.token.strip()}"
        try:
            with httpx.Client(
                base_url=self.base_url.rstrip("/"), headers=headers, timeout=30
            ) as client:
                response = client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise ApiError(f"无法连接后端：{exc}") from exc
        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise ApiError(f"后端返回 {response.status_code}：{detail}")
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("POST", path, json=payload)

    def put(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("PUT", path, json=payload)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)
