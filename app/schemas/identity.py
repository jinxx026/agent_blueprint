"""HTTP contracts for identity discovery and local development tokens."""

from pydantic import BaseModel, ConfigDict, Field

from app.identity import RequestContext


class DevelopmentTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str = Field(min_length=1, max_length=128)
    user_id: str = Field(min_length=1, max_length=256)
    roles: tuple[str, ...] = Field(min_length=1)


class DevelopmentTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class SessionResponse(RequestContext):
    pass
