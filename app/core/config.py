"""Typed application configuration loaded from environment variables."""

from enum import StrEnum
from functools import lru_cache

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    """Supported deployment environments."""

    LOCAL = "local"
    TEST = "test"
    PRODUCTION = "production"


class AuthMode(StrEnum):
    """Identity verification strategy used by the API boundary."""

    DEVELOPMENT = "development"
    JWT = "jwt"
    OIDC = "oidc"


class Settings(BaseSettings):
    """Validated process configuration.

    Every environment variable starts with ``AGENTBLUEPRINT_``. Secrets will later
    be represented by secret references rather than Blueprint fields.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AGENTBLUEPRINT_",
        extra="ignore",
        frozen=True,
    )

    app_name: str = "AgentBlueprint API"
    app_version: str = "0.1.0"
    environment: AppEnvironment = AppEnvironment.LOCAL
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    docs_enabled: bool = True
    database_path: str = "data/agentblueprint.db"
    auth_mode: AuthMode = AuthMode.DEVELOPMENT
    auth_issuer: str = "agentblueprint-local"
    auth_audience: str = "agentblueprint-api"
    auth_jwks_url: str | None = None
    auth_hs256_secret: SecretStr = SecretStr(
        "development-only-change-this-secret-before-production"
    )
    auth_organization_claim: str = "organization_id"
    auth_roles_claim: str = "roles"
    development_organization_id: str = "demo-company"
    development_user_id: str = "local-developer"
    development_roles: tuple[str, ...] = (
        "organization_admin",
        "ai_developer",
        "customer_service",
        "supervisor",
    )
    cors_origins: tuple[str, ...] = (
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    )

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        """Require a stable absolute prefix without a trailing slash."""

        if not value.startswith("/"):
            raise ValueError("api_v1_prefix must start with '/'")
        if value != "/" and value.endswith("/"):
            raise ValueError("api_v1_prefix must not end with '/'")
        return value

    @model_validator(mode="after")
    def validate_identity_settings(self) -> "Settings":
        if self.environment is AppEnvironment.PRODUCTION and self.auth_mode is AuthMode.DEVELOPMENT:
            raise ValueError("production cannot use development authentication")
        if self.auth_mode is AuthMode.OIDC and not self.auth_jwks_url:
            raise ValueError("OIDC authentication requires auth_jwks_url")
        if self.auth_mode is AuthMode.JWT and len(self.auth_hs256_secret.get_secret_value()) < 32:
            raise ValueError(
                "JWT authentication requires an HS256 secret of at least 32 characters"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Load and cache one immutable Settings instance per process."""

    return Settings()
