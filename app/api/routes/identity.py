"""Identity discovery plus an explicitly local-only token issuer."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_request_context
from app.core.config import AuthMode
from app.identity import RequestContext
from app.schemas.identity import (
    DevelopmentTokenRequest,
    DevelopmentTokenResponse,
    SessionResponse,
)

router = APIRouter()


@router.get("/session", response_model=SessionResponse)
def get_session(context: Annotated[RequestContext, Depends(get_request_context)]) -> RequestContext:
    return context


@router.post("/development-token", response_model=DevelopmentTokenResponse)
def create_development_token(
    payload: DevelopmentTokenRequest,
    request: Request,
) -> DevelopmentTokenResponse:
    settings = request.app.state.settings
    if settings.auth_mode is not AuthMode.DEVELOPMENT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    request.app.state.control_plane_store.provision_identity(
        organization_id=payload.organization_id,
        user_id=payload.user_id,
        roles=payload.roles,
    )
    token = request.app.state.authenticator.issue_development_token(
        organization_id=payload.organization_id,
        user_id=payload.user_id,
        roles=payload.roles,
    )
    return DevelopmentTokenResponse(access_token=token)
