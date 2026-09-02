"""Small HTTP client used by every Streamlit page."""

import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx


class ApiError(RuntimeError):
    """A readable backend error that can be shown directly in the UI."""


@lru_cache(maxsize=1)
def embedded_client():
    """Load FastAPI inside Streamlit for a zero-configuration cloud demo."""

    backend_root = Path(__file__).resolve().parents[1] / "backend"
    backend_path = str(backend_root)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


@dataclass(frozen=True)
class ApiClient:
    base_url: str
    token: str = ""

    @property
    def is_embedded(self) -> bool:
        return self.base_url.strip().lower() == "embedded"

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = {"Accept": "application/json"}
        if self.token.strip():
            headers["Authorization"] = f"Bearer {self.token.strip()}"
        try:
            if self.is_embedded:
                response = embedded_client().request(
                    method, f"/api/v1{path}", headers=headers, **kwargs
                )
            else:
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
