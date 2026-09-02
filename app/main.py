"""FastAPI application assembly.

This module is the composition root: it creates the web application and connects
configuration with API routers. Business logic must live in dedicated modules.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import AuthMode, Settings, get_settings
from app.identity import Authenticator
from app.runtime import BlueprintExecutor
from app.storage import ControlPlaneStore


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an isolated application instance.

    Supplying settings makes tests deterministic. Normal application startup uses
    the cached environment-backed settings returned by ``get_settings``.
    """

    resolved_settings = settings or get_settings()
    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.debug,
        docs_url="/docs" if resolved_settings.docs_enabled else None,
        redoc_url="/redoc" if resolved_settings.docs_enabled else None,
        openapi_url="/openapi.json" if resolved_settings.docs_enabled else None,
    )
    application.state.settings = resolved_settings
    application.state.authenticator = Authenticator(resolved_settings)
    application.state.blueprint_executor = BlueprintExecutor()
    application.state.control_plane_store = ControlPlaneStore(resolved_settings.database_path)
    if resolved_settings.auth_mode is AuthMode.DEVELOPMENT:
        application.state.control_plane_store.provision_identity(
            organization_id=resolved_settings.development_organization_id,
            user_id=resolved_settings.development_user_id,
            roles=resolved_settings.development_roles,
            display_name="Local developer",
        )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=resolved_settings.api_v1_prefix)
    return application


app = create_app()
