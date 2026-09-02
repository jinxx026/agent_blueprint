"""Authentication providers that keep secrets outside Blueprint files."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NoAuth:
    def headers(self) -> dict[str, str]:
        return {}


@dataclass(frozen=True)
class BearerTokenAuth:
    token: str = field(repr=False)

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


@dataclass(frozen=True)
class ApiKeyAuth:
    api_key: str = field(repr=False)
    header_name: str = "X-API-Key"

    def headers(self) -> dict[str, str]:
        return {self.header_name: self.api_key}
