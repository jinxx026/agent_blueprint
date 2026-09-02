"""Request-scoped API dependencies."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.blueprint.service import BlueprintService
from app.compiler import BlueprintCompiler
from app.core.config import Settings
from app.evaluation import EvaluationRunner
from app.identity import AuthenticationError, Authenticator, RequestContext
from app.runtime import BlueprintExecutor
from app.storage import ControlPlaneStore


def get_request_settings(request: Request) -> Settings:
    """Return the settings attached to the current application instance."""

    return request.app.state.settings


def get_authenticator(request: Request) -> Authenticator:
    return request.app.state.authenticator


def get_control_plane_store(request: Request) -> ControlPlaneStore:
    """Return the app-scoped tenant-aware persistent store."""

    return request.app.state.control_plane_store


def get_request_context(
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    authorization: Annotated[str | None, Header()] = None,
) -> RequestContext:
    """Verify the caller and return server-owned organization and role claims."""

    try:
        context = authenticator.authenticate(authorization)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    try:
        membership = store.get_membership(context.organization_id, context.user_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not an active member of this organization",
        ) from exc
    if membership["status"] != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Membership is inactive")
    return context.model_copy(update={"roles": tuple(membership["roles"])})


def get_blueprint_service() -> BlueprintService:
    """Create the stateless Blueprint validation application service."""

    return BlueprintService()


def get_blueprint_compiler() -> BlueprintCompiler:
    """Create the deterministic, framework-independent Blueprint Compiler."""

    return BlueprintCompiler()


def get_blueprint_executor(request: Request) -> BlueprintExecutor:
    """Return the app-scoped executor so interrupted graphs can be resumed."""

    return request.app.state.blueprint_executor


def get_evaluation_runner(request: Request) -> EvaluationRunner:
    """Evaluate with the same runtime adapters used by normal executions."""

    return EvaluationRunner(get_blueprint_executor(request))
