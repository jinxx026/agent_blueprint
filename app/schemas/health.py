"""Health endpoint response contract."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.core.config import AppEnvironment


class HealthStatus(StrEnum):
    """Possible process-level health values."""

    OK = "ok"


class HealthResponse(BaseModel):
    """Public, non-secret service metadata returned by the health endpoint."""

    model_config = ConfigDict(extra="forbid")

    status: HealthStatus
    service: str
    version: str
    environment: AppEnvironment
