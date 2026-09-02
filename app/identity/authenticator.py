"""JWT and OIDC verification that produces an authoritative RequestContext."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError, PyJWKClient

from app.core.config import AuthMode, Settings
from app.identity.models import RequestContext


class AuthenticationError(ValueError):
    """Raised when the caller cannot be mapped to a trusted enterprise identity."""


class Authenticator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._jwk_client = (
            PyJWKClient(settings.auth_jwks_url)
            if settings.auth_mode is AuthMode.OIDC and settings.auth_jwks_url
            else None
        )

    def authenticate(self, authorization: str | None) -> RequestContext:
        if not authorization:
            if self._settings.auth_mode is AuthMode.DEVELOPMENT:
                return self._development_context()
            raise AuthenticationError("Missing bearer token")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthenticationError("Authorization must use the Bearer scheme")
        try:
            claims = self._decode(token)
            return self._context_from_claims(claims)
        except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError("Invalid or expired access token") from exc

    def issue_development_token(
        self,
        *,
        organization_id: str,
        user_id: str,
        roles: tuple[str, ...],
        expires_in: timedelta = timedelta(hours=1),
    ) -> str:
        """Create a local HS256 token; unavailable in production and OIDC modes."""

        if self._settings.auth_mode is not AuthMode.DEVELOPMENT:
            raise AuthenticationError("Development tokens are disabled")
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "iss": self._settings.auth_issuer,
                "aud": self._settings.auth_audience,
                "sub": user_id,
                self._settings.auth_organization_claim: organization_id,
                self._settings.auth_roles_claim: list(roles),
                "iat": now,
                "exp": now + expires_in,
            },
            self._settings.auth_hs256_secret.get_secret_value(),
            algorithm="HS256",
        )

    def _decode(self, token: str) -> dict[str, Any]:
        if self._settings.auth_mode is AuthMode.OIDC:
            if self._jwk_client is None:
                raise AuthenticationError("OIDC key provider is not configured")
            key = self._jwk_client.get_signing_key_from_jwt(token).key
            return jwt.decode(
                token,
                key,
                algorithms=["RS256", "ES256"],
                audience=self._settings.auth_audience,
                issuer=self._settings.auth_issuer,
            )
        return jwt.decode(
            token,
            self._settings.auth_hs256_secret.get_secret_value(),
            algorithms=["HS256"],
            audience=self._settings.auth_audience,
            issuer=self._settings.auth_issuer,
        )

    def _context_from_claims(self, claims: dict[str, Any]) -> RequestContext:
        raw_roles = claims.get(self._settings.auth_roles_claim, ())
        roles = (raw_roles,) if isinstance(raw_roles, str) else tuple(raw_roles)
        return RequestContext(
            organization_id=str(claims[self._settings.auth_organization_claim]),
            user_id=str(claims["sub"]),
            roles=tuple(str(role) for role in roles),
            email=str(claims["email"]) if claims.get("email") else None,
            display_name=str(claims["name"]) if claims.get("name") else None,
        )

    def _development_context(self) -> RequestContext:
        return RequestContext(
            organization_id=self._settings.development_organization_id,
            user_id=self._settings.development_user_id,
            roles=self._settings.development_roles,
            display_name="Local developer",
        )
