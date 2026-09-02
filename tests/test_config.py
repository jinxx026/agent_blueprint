"""Configuration behavior tests."""

import pytest
from pydantic import ValidationError

from app.core.config import AppEnvironment, AuthMode, Settings


def test_settings_load_prefixed_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTBLUEPRINT_APP_NAME", "Configured API")
    monkeypatch.setenv("AGENTBLUEPRINT_ENVIRONMENT", "production")
    monkeypatch.setenv("AGENTBLUEPRINT_AUTH_MODE", "jwt")
    monkeypatch.setenv("AGENTBLUEPRINT_DEBUG", "true")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Configured API"
    assert settings.environment is AppEnvironment.PRODUCTION
    assert settings.auth_mode is AuthMode.JWT
    assert settings.debug is True


@pytest.mark.parametrize("prefix", ["api/v1", "/api/v1/"])
def test_settings_reject_invalid_api_prefix(prefix: str) -> None:
    with pytest.raises(ValidationError):
        Settings(api_v1_prefix=prefix, _env_file=None)


def test_production_rejects_development_authentication() -> None:
    with pytest.raises(ValidationError, match="production cannot use development authentication"):
        Settings(environment=AppEnvironment.PRODUCTION, _env_file=None)
