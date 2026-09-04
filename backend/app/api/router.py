"""Top-level API router composition."""

from fastapi import APIRouter

from app.api.routes import apps, blueprints, control_plane, executions, health, identity

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(identity.router, prefix="/auth", tags=["identity"])
api_router.include_router(blueprints.router, prefix="/blueprints", tags=["blueprints"])
api_router.include_router(executions.router, prefix="/executions", tags=["executions"])
api_router.include_router(control_plane.router, prefix="/control", tags=["control-plane"])
api_router.include_router(apps.router, prefix="/apps", tags=["published-apps"])
