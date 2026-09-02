"""Shared pytest fixtures."""

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from app.core.config import AppEnvironment, Settings
from app.main import create_app


@pytest.fixture
def example_blueprint_path() -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "customer-support" / "blueprint.yaml"


@pytest.fixture
def example_blueprint_data(example_blueprint_path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(example_blueprint_path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture
def test_settings() -> Settings:
    """Return deterministic settings independent of the developer machine."""

    return Settings(
        app_name="AgentBlueprint Test API",
        app_version="0.1.0-test",
        environment=AppEnvironment.TEST,
        debug=True,
        docs_enabled=True,
        database_path=":memory:",
        _env_file=None,
    )


@pytest.fixture
def client(test_settings: Settings) -> Iterator[TestClient]:
    """Create and close an in-process HTTP client for each test."""

    with TestClient(create_app(test_settings)) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient) -> Callable[[str, tuple[str, ...]], dict[str, str]]:
    """Issue trusted local tokens so tests can exercise organization boundaries."""

    def issue(
        organization_id: str,
        roles: tuple[str, ...] = (
            "organization_admin",
            "ai_developer",
            "customer_service",
            "supervisor",
        ),
    ) -> dict[str, str]:
        response = client.post(
            "/api/v1/auth/development-token",
            json={
                "organization_id": organization_id,
                "user_id": f"user-{organization_id}",
                "roles": list(roles),
            },
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return issue
