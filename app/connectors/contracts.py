"""Framework-neutral connector request and response contracts."""

from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict


class ConnectorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: str
    arguments: dict[str, Any]
    idempotency_key: str | None = None


class ConnectorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    data: Any
    status_code: int = 200


class Connector(Protocol):
    def invoke(self, request: ConnectorRequest) -> ConnectorResponse: ...


class AuthProvider(Protocol):
    def headers(self) -> Mapping[str, str]: ...
