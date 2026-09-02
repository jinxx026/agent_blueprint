"""HTTP adapter with explicit operation paths, authentication, and timeouts."""

from dataclasses import dataclass, field

import httpx

from app.connectors.auth import NoAuth
from app.connectors.contracts import AuthProvider, ConnectorRequest, ConnectorResponse
from app.connectors.errors import (
    ConnectorNotFoundError,
    ConnectorPermanentError,
    ConnectorTemporaryError,
)


@dataclass(frozen=True)
class HttpConnectorConfig:
    base_url: str
    operation_paths: dict[str, str]
    timeout_seconds: float = 10.0
    auth: AuthProvider = field(default_factory=NoAuth)


class HttpConnector:
    def __init__(self, config: HttpConnectorConfig, transport: httpx.BaseTransport | None = None):
        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            transport=transport,
        )

    def invoke(self, request: ConnectorRequest) -> ConnectorResponse:
        path = self._config.operation_paths.get(request.operation)
        if path is None:
            raise ConnectorNotFoundError(f"HTTP operation '{request.operation}' is not mapped")
        headers = dict(self._config.auth.headers())
        if request.idempotency_key:
            headers["Idempotency-Key"] = request.idempotency_key
        try:
            response = self._client.post(path, json=request.arguments, headers=headers)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ConnectorTemporaryError("Enterprise system is temporarily unavailable") from exc

        if response.status_code == 429 or response.status_code >= 500:
            raise ConnectorTemporaryError(
                f"Enterprise system returned temporary status {response.status_code}"
            )
        if response.status_code >= 400:
            raise ConnectorPermanentError(
                f"Enterprise system rejected the request with status {response.status_code}"
            )
        try:
            data = response.json()
        except ValueError:
            data = response.text
        return ConnectorResponse(data=data, status_code=response.status_code)

    def close(self) -> None:
        self._client.close()
