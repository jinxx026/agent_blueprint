from fastapi.testclient import TestClient


def test_development_session_has_server_owned_demo_identity(client: TestClient) -> None:
    response = client.get("/api/v1/auth/session")

    assert response.status_code == 200
    assert response.json()["organization_id"] == "demo-company"
    assert "organization_admin" in response.json()["roles"]


def test_signed_token_controls_organization_even_when_body_is_forged(
    client: TestClient,
    example_blueprint_path,
    auth_headers,
) -> None:
    response = client.post(
        "/api/v1/control/blueprints",
        json={
            "tenant_id": "victim-company",
            "content": example_blueprint_path.read_text(encoding="utf-8"),
            "format": "yaml",
        },
        headers=auth_headers("authenticated-company"),
    )

    assert response.status_code == 201
    assert response.json()["tenant_id"] == "authenticated-company"


def test_tampered_token_is_rejected(client: TestClient, auth_headers) -> None:
    token = auth_headers("acme")["Authorization"]
    response = client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"{token}tampered"},
    )

    assert response.status_code == 401


def test_valid_token_without_platform_membership_is_rejected(client: TestClient) -> None:
    token = client.app.state.authenticator.issue_development_token(
        organization_id="unprovisioned-company",
        user_id="unknown-user",
        roles=("organization_admin",),
    )

    response = client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User is not an active member of this organization"
