import httpx

from app.connectors.auth import BearerTokenAuth
from app.connectors.contracts import ConnectorRequest
from app.connectors.http import HttpConnector, HttpConnectorConfig


def test_http_connector_applies_auth_timeout_route_and_idempotency_header() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["idempotency"] = request.headers["Idempotency-Key"]
        return httpx.Response(200, json={"order_id": "O-1"})

    auth = BearerTokenAuth("secret-token")
    connector = HttpConnector(
        HttpConnectorConfig(
            base_url="https://orders.example.test",
            operation_paths={"get_order": "/v1/orders/get"},
            timeout_seconds=2,
            auth=auth,
        ),
        transport=httpx.MockTransport(handler),
    )

    response = connector.invoke(
        ConnectorRequest(
            operation="get_order",
            arguments={"order_id": "O-1"},
            idempotency_key="idem-1",
        )
    )

    assert response.data == {"order_id": "O-1"}
    assert captured == {
        "url": "https://orders.example.test/v1/orders/get",
        "authorization": "Bearer secret-token",
        "idempotency": "idem-1",
    }
    assert "secret-token" not in repr(auth)
