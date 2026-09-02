"""Identity objects trusted by application services after token verification."""

from pydantic import BaseModel, ConfigDict, Field


class RequestContext(BaseModel):
    """Server-derived identity attached to one API request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    organization_id: str = Field(min_length=1, max_length=128)
    user_id: str = Field(min_length=1, max_length=256)
    roles: tuple[str, ...] = ()
    email: str | None = None
    display_name: str | None = None

    def has_any_role(self, *required: str) -> bool:
        return bool(set(required).intersection(self.roles))
