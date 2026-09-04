"""Persistent Blueprint, knowledge, evaluation, and release APIs."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import (
    get_blueprint_compiler,
    get_blueprint_executor,
    get_blueprint_service,
    get_control_plane_store,
    get_evaluation_runner,
    get_request_context,
)
from app.blueprint.loader import BlueprintFormat
from app.blueprint.service import BlueprintService
from app.compiler import BlueprintCompiler
from app.evaluation import EvaluationRunner
from app.identity import RequestContext
from app.modules import MODULE_CATALOG, get_module_template
from app.rag import RagDocument
from app.rag.pdf_parser import PdfIngestionError, parse_pdf
from app.runtime import BlueprintExecutor
from app.runtime.executor import ExecutionResult
from app.schemas.control_plane import (
    BlueprintRecord,
    BlueprintSaveRequest,
    BlueprintVersionRecord,
    BusinessModuleRecord,
    DeploymentRecord,
    EvaluationRecord,
    KnowledgeDocumentCreate,
    KnowledgeDocumentRecord,
    ModuleInstallRequest,
    PdfIngestionResponse,
    PublishRequest,
    StoredBlueprintExecutionRequest,
    StoredEvaluationRequest,
)
from app.storage import ControlPlaneStore

router = APIRouter()


def require_module_admin(context: RequestContext) -> None:
    if not context.has_any_role("organization_admin", "ai_developer"):
        raise HTTPException(status_code=403, detail="Module administration role required")


def validated_plan(
    content: str,
    source_format: BlueprintFormat,
    service: BlueprintService,
    compiler: BlueprintCompiler,
):
    validation = service.validate_text(content, source_format)
    if not validation.is_valid or validation.blueprint is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[issue.__dict__ for issue in validation.errors],
        )
    return validation.blueprint, compiler.compile(validation.blueprint)


@router.post("/blueprints", response_model=BlueprintRecord, status_code=201)
def save_blueprint(
    request: BlueprintSaveRequest,
    service: Annotated[BlueprintService, Depends(get_blueprint_service)],
    compiler: Annotated[BlueprintCompiler, Depends(get_blueprint_compiler)],
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict[str, object]:
    blueprint, plan = validated_plan(request.content, request.format, service, compiler)
    return store.save_blueprint(
        tenant_id=context.organization_id,
        name=blueprint.metadata.name,
        display_name=blueprint.metadata.display_name,
        version=blueprint.metadata.version,
        content=request.content,
        source_format=str(request.format),
        content_hash=plan.source.content_hash,
    )


@router.get("/blueprints", response_model=list[BlueprintRecord])
def list_blueprints(
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> list[dict[str, object]]:
    return store.list_blueprints(context.organization_id)


@router.get("/blueprints/{blueprint_id}", response_model=BlueprintRecord)
def get_blueprint(
    blueprint_id: str,
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict[str, object]:
    try:
        return store.get_blueprint(context.organization_id, blueprint_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Blueprint not found") from exc


@router.get("/blueprints/{blueprint_id}/versions", response_model=list[BlueprintVersionRecord])
def list_blueprint_versions(
    blueprint_id: str,
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> list[dict[str, object]]:
    return store.list_versions(context.organization_id, blueprint_id)


@router.post("/blueprints/{blueprint_id}/execute", response_model=ExecutionResult)
def preview_stored_blueprint(
    blueprint_id: str,
    request: StoredBlueprintExecutionRequest,
    service: Annotated[BlueprintService, Depends(get_blueprint_service)],
    compiler: Annotated[BlueprintCompiler, Depends(get_blueprint_compiler)],
    executor: Annotated[BlueprintExecutor, Depends(get_blueprint_executor)],
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> ExecutionResult:
    from app.api.routes.apps import _knowledge_store

    try:
        record = store.get_blueprint(context.organization_id, blueprint_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Blueprint not found") from exc
    validation = service.validate_text(
        str(record["content"]), BlueprintFormat(str(record["format"]))
    )
    if not validation.is_valid or validation.blueprint is None:
        raise HTTPException(status_code=422, detail="Stored Blueprint is invalid")
    knowledge = _knowledge_store(
        store.list_knowledge_documents(context.organization_id),
        context.organization_id,
        context.roles,
    )
    return executor.execute(
        compiler.compile(validation.blueprint),
        request.message,
        request.thread_id,
        policy_context=request.policy_context,
        actor_roles=context.roles,
        knowledge=knowledge,
    )


@router.post("/knowledge-documents", response_model=KnowledgeDocumentRecord, status_code=201)
def create_knowledge_document(
    request: KnowledgeDocumentCreate,
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict[str, object]:
    values = request.model_dump(exclude={"tenant_id"})
    return store.add_knowledge_document(tenant_id=context.organization_id, **values)


@router.post("/knowledge-documents/pdf", response_model=PdfIngestionResponse, status_code=201)
async def upload_knowledge_pdf(
    file: Annotated[UploadFile, File(description="Text-based enterprise PDF")],
    source_id: Annotated[str, Form(min_length=2, max_length=128)],
    allowed_roles: Annotated[str, Form()] = "customer_service,supervisor",
    citation_base: Annotated[str, Form()] = "knowledge://customer-service/after-sales-policy",
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)] = None,
    context: Annotated[RequestContext, Depends(get_request_context)] = None,
) -> dict[str, object]:
    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(status_code=415, detail="只支持 PDF 文件")
    try:
        parsed = parse_pdf(await file.read())
    except PdfIngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    roles = tuple(dict.fromkeys(item.strip() for item in allowed_roles.split(",") if item.strip()))
    if not roles:
        raise HTTPException(status_code=422, detail="至少需要一个可访问角色")
    document = store.add_knowledge_document(
        tenant_id=context.organization_id,
        source_id=source_id,
        title=file.filename or "售后政策.pdf",
        content=parsed.content,
        allowed_roles=roles,
        citation_base=citation_base,
    )
    return {
        "document": document,
        "page_count": parsed.page_count,
        "character_count": parsed.character_count,
    }


@router.get("/knowledge-documents", response_model=list[KnowledgeDocumentRecord])
def list_knowledge_documents(
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> list[dict[str, object]]:
    return store.list_knowledge_documents(context.organization_id)


@router.get("/modules", response_model=list[BusinessModuleRecord])
def list_business_modules(
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> list[dict[str, object]]:
    installed = {
        str(item["module_key"]): item
        for item in store.list_module_installations(context.organization_id)
    }
    return [
        {
            **template,
            "installed": template["key"] in installed,
            "installation_id": installed.get(template["key"], {}).get("id"),
            "rag": installed.get(template["key"], {}).get("rag"),
            "updated_at": installed.get(template["key"], {}).get("updated_at"),
        }
        for template in MODULE_CATALOG
    ]


@router.put("/modules/{module_key}", response_model=BusinessModuleRecord)
def install_business_module(
    module_key: str,
    request: ModuleInstallRequest,
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict[str, object]:
    require_module_admin(context)
    try:
        template = get_module_template(module_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Module template not found") from exc
    installation = store.upsert_module_installation(
        context.organization_id,
        module_key,
        request.rag.model_dump(mode="json"),
    )
    return {
        **template,
        "installed": True,
        "installation_id": installation["id"],
        "rag": installation["rag"],
        "updated_at": installation["updated_at"],
    }


@router.delete("/modules/{module_key}", status_code=204)
def uninstall_business_module(
    module_key: str,
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> None:
    require_module_admin(context)
    try:
        store.remove_module_installation(context.organization_id, module_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Installed module not found") from exc


@router.post("/blueprints/{blueprint_id}/evaluations", response_model=EvaluationRecord)
def evaluate_stored_blueprint(
    blueprint_id: str,
    request: StoredEvaluationRequest,
    service: Annotated[BlueprintService, Depends(get_blueprint_service)],
    compiler: Annotated[BlueprintCompiler, Depends(get_blueprint_compiler)],
    runner: Annotated[EvaluationRunner, Depends(get_evaluation_runner)],
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict[str, object]:
    organization_id = context.organization_id
    try:
        record = store.get_blueprint(organization_id, blueprint_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Blueprint not found") from exc
    blueprint, plan = validated_plan(
        str(record["content"]), BlueprintFormat(str(record["format"])), service, compiler
    )
    documents = store.list_knowledge_documents(organization_id)
    rag_documents = (
        tuple(
            RagDocument(
                tenant_id=organization_id,
                source_id=str(item["source_id"]),
                document_id=str(item["id"]),
                title=str(item["title"]),
                content=str(item["content"]),
                allowed_roles=frozenset(item["allowed_roles"]),
                citation_base=str(item["citation_base"]),
            )
            for item in documents
        )
        if request.use_stored_knowledge
        else ()
    )
    report = runner.run(
        blueprint,
        plan,
        request.cases,
        rag_documents=rag_documents,
        tenant_id=organization_id,
    )
    return store.save_evaluation(
        organization_id,
        blueprint_id,
        str(record["version"]),
        report.model_dump(mode="json"),
    )


@router.get("/blueprints/{blueprint_id}/evaluations", response_model=list[EvaluationRecord])
def list_evaluations(
    blueprint_id: str,
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> list[dict[str, object]]:
    return store.list_evaluations(context.organization_id, blueprint_id)


@router.post("/blueprints/{blueprint_id}/publish", response_model=DeploymentRecord)
def publish_blueprint(
    blueprint_id: str,
    request: PublishRequest,
    store: Annotated[ControlPlaneStore, Depends(get_control_plane_store)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict[str, object]:
    try:
        deployment = store.publish(context.organization_id, blueprint_id, request.environment)
        return {
            **deployment,
            "endpoint": f"/api/v1/apps/{blueprint_id}/invoke",
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Blueprint not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
