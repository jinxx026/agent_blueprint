"""Resolve Blueprint connector references to concrete adapters."""

from collections.abc import Callable, Mapping

from app.connectors.contracts import Connector, ConnectorRequest, ConnectorResponse
from app.connectors.errors import ConnectorNotFoundError


class ConnectorRegistry:
    def __init__(self, connectors: Mapping[str, Connector] | None = None) -> None:
        self._connectors = dict(connectors or {})

    def register(self, connector_ref: str, connector: Connector) -> None:
        self._connectors[connector_ref] = connector

    def resolve(self, connector_ref: str) -> Connector:
        try:
            return self._connectors[connector_ref]
        except KeyError as exc:
            raise ConnectorNotFoundError(f"Connector '{connector_ref}' is not registered") from exc


class FunctionConnector:
    """Test/local adapter that behaves like a real connector."""

    def __init__(self, operations: Mapping[str, Callable[[dict[str, object]], object]]) -> None:
        self._operations = dict(operations)

    def invoke(self, request: ConnectorRequest) -> ConnectorResponse:
        try:
            handler = self._operations[request.operation]
        except KeyError as exc:
            raise ConnectorNotFoundError(
                f"Operation '{request.operation}' is not registered"
            ) from exc
        return ConnectorResponse(data=handler(request.arguments))
