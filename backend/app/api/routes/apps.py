"""Callable API for evaluated and published enterprise AI applications."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import (
    get_blueprint_compiler,
    get_blueprint_executor,
    get_blueprint_service,
    get_control_plane_store,
    get_request_context,
)
from app.blueprint.loader import BlueprintFormat
from app.blueprint.service import BlueprintService
from app.compiler import BlueprintCompiler
from app.identity import RequestContext
from app.rag import RagDocument, RagKnowledgeStore, create_local_rag_pipeline
from app.runtime import BlueprintExecutor
from app.schemas.control_plane import PublishedInvocationResponse, StoredBlueprintExecutionRequest
from app.storage import ControlPlaneStore

router = APIRouter()


def _knowledge_store(
    records: list[dict[str, object]], tenant_id: str, roles: tuple[str, ...]
) -> RagKnowledgeStore:
    pipeline = create_local_rag_pipeline()
    pipeline.ingest(
        [
            RagDocument(
                tenant_id=tenant_id,
                source_id=str(item["source_id"]),
                document_id=str(item["id"]),
                title=str(item["title"]),
                content=str(item["content"]),
                allowed_roles=frozenset(item["allowed_roles"]),
                citation_base=str(item["citation_base"]),
            )
            for item in records
        ]
    )
    return RagKnowledgeStore(pipeline, tenant_id, frozenset(roles))


@router.post("/{blueprint_id}/invoke", response_model=PublishedInvocationResponse)
def invoke_published_app(
    blueprint_id: str,
    request: StoredBlueprintExecutionRequest,
    service: Annotated[BlueprintService, Depends(get_blueprint_service)],
    compiler: Annotated[BlueprintCompiler, Depends(get_blueprint_compiler)],
    executor: Annotated[BlueprintExecutor, Depends(get_blueprint_executor)],
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict[str, object]:
    try:
        record = store.get_blueprint(context.organization_id, blueprint_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Blueprint not found") from exc
    if str(record["stage"]) not in {"test", "production"}:
        raise HTTPException(status_code=409, detail="Blueprint has not been published")
    validation = service.validate_text(
        str(record["content"]), BlueprintFormat(str(record["format"]))
    )
    if not validation.is_valid or validation.blueprint is None:
        raise HTTPException(status_code=422, detail="Stored Blueprint is invalid")
    plan = compiler.compile(validation.blueprint)
    knowledge = _knowledge_store(
        store.list_knowledge_documents(context.organization_id),
        context.organization_id,
        context.roles,
    )
    result = executor.execute(
        plan,
        request.message,
        request.thread_id,
        policy_context=request.policy_context,
        actor_roles=context.roles,
        knowledge=knowledge,
    )
    return {"blueprint_id": blueprint_id, "result": result}
