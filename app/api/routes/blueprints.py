"""Blueprint authoring and validation endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import (
    get_blueprint_compiler,
    get_blueprint_executor,
    get_blueprint_service,
    get_evaluation_runner,
    get_request_context,
)
from app.blueprint.service import BlueprintService
from app.compiler import BlueprintCompiler, CompilationError
from app.evaluation import EvaluationRunner
from app.identity import RequestContext
from app.rag import RagKnowledgeStore, create_local_rag_pipeline
from app.runtime import BlueprintExecutor, MemoryKnowledgeStore
from app.schemas.blueprint import (
    BlueprintCompilationResponse,
    BlueprintExecutionRequest,
    BlueprintExecutionResponse,
    BlueprintIssueResponse,
    BlueprintReleaseCheckRequest,
    BlueprintReleaseCheckResponse,
    BlueprintValidationRequest,
    BlueprintValidationResponse,
)

router = APIRouter()


@router.post(
    "/validate",
    response_model=BlueprintValidationResponse,
    summary="Validate a Blueprint without saving it",
)
def validate_blueprint(
    request: BlueprintValidationRequest,
    service: Annotated[BlueprintService, Depends(get_blueprint_service)],
) -> BlueprintValidationResponse:
    """Safely parse and validate inline YAML or JSON content."""

    result = service.validate_text(request.content, request.format)
    return BlueprintValidationResponse.from_domain(result)


@router.post(
    "/compile",
    response_model=BlueprintCompilationResponse,
    summary="Validate and compile a Blueprint into an ExecutionPlan",
)
def compile_blueprint(
    request: BlueprintValidationRequest,
    service: Annotated[BlueprintService, Depends(get_blueprint_service)],
    compiler: Annotated[BlueprintCompiler, Depends(get_blueprint_compiler)],
) -> BlueprintCompilationResponse:
    """Compile inline authoring content without saving or executing the plan."""

    validation = service.validate_text(request.content, request.format)
    warnings = [BlueprintIssueResponse.from_domain(issue) for issue in validation.warnings]
    if not validation.is_valid or validation.blueprint is None:
        return BlueprintCompilationResponse(
            compiled=False,
            plan=None,
            errors=[BlueprintIssueResponse.from_domain(issue) for issue in validation.errors],
            warnings=warnings,
        )

    try:
        plan = compiler.compile(validation.blueprint)
    except CompilationError as exc:
        return BlueprintCompilationResponse(
            compiled=False,
            plan=None,
            errors=[
                BlueprintIssueResponse.from_compiler(diagnostic) for diagnostic in exc.diagnostics
            ],
            warnings=warnings,
        )

    return BlueprintCompilationResponse(
        compiled=True,
        plan=plan,
        errors=[],
        warnings=warnings,
    )


@router.post(
    "/execute",
    response_model=BlueprintExecutionResponse,
    summary="Compile and execute a Blueprint with the local LangGraph runtime",
)
def execute_blueprint(
    request: BlueprintExecutionRequest,
    service: Annotated[BlueprintService, Depends(get_blueprint_service)],
    compiler: Annotated[BlueprintCompiler, Depends(get_blueprint_compiler)],
    executor: Annotated[BlueprintExecutor, Depends(get_blueprint_executor)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> BlueprintExecutionResponse:
    """Run a Blueprint with supplied in-memory knowledge and the offline model."""

    validation = service.validate_text(request.content, request.format)
    warnings = [BlueprintIssueResponse.from_domain(issue) for issue in validation.warnings]
    if not validation.is_valid or validation.blueprint is None:
        return BlueprintExecutionResponse(
            executed=False,
            result=None,
            errors=[BlueprintIssueResponse.from_domain(issue) for issue in validation.errors],
            warnings=warnings,
        )

    try:
        plan = compiler.compile(validation.blueprint)
    except CompilationError as exc:
        return BlueprintExecutionResponse(
            executed=False,
            result=None,
            errors=[
                BlueprintIssueResponse.from_compiler(diagnostic) for diagnostic in exc.diagnostics
            ],
            warnings=warnings,
        )

    if request.rag_documents:
        if any(document.tenant_id != context.organization_id for document in request.rag_documents):
            raise HTTPException(status_code=403, detail="RAG document organization mismatch")
        pipeline = create_local_rag_pipeline()
        pipeline.ingest(request.rag_documents)
        knowledge = RagKnowledgeStore(
            pipeline,
            tenant_id=context.organization_id,
            roles=frozenset(context.roles),
        )
    else:
        knowledge = MemoryKnowledgeStore(request.knowledge_documents)
    result = executor.execute(
        plan,
        request.message,
        request.thread_id,
        policy_context=request.policy_context,
        actor_roles=context.roles,
        knowledge=knowledge,
    )
    return BlueprintExecutionResponse(
        executed=True,
        result=result,
        errors=[],
        warnings=warnings,
    )


@router.post(
    "/release-check",
    response_model=BlueprintReleaseCheckResponse,
    summary="Run the Blueprint evaluation suite and enforce its release gate",
)
def release_check_blueprint(
    request: BlueprintReleaseCheckRequest,
    service: Annotated[BlueprintService, Depends(get_blueprint_service)],
    compiler: Annotated[BlueprintCompiler, Depends(get_blueprint_compiler)],
    runner: Annotated[EvaluationRunner, Depends(get_evaluation_runner)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> BlueprintReleaseCheckResponse:
    """Return a report instead of publishing when any gate condition fails."""

    validation = service.validate_text(request.content, request.format)
    warnings = [BlueprintIssueResponse.from_domain(issue) for issue in validation.warnings]
    if not validation.is_valid or validation.blueprint is None:
        return BlueprintReleaseCheckResponse(
            evaluated=False,
            report=None,
            errors=[BlueprintIssueResponse.from_domain(issue) for issue in validation.errors],
            warnings=warnings,
        )

    try:
        plan = compiler.compile(validation.blueprint)
    except CompilationError as exc:
        return BlueprintReleaseCheckResponse(
            evaluated=False,
            report=None,
            errors=[
                BlueprintIssueResponse.from_compiler(diagnostic) for diagnostic in exc.diagnostics
            ],
            warnings=warnings,
        )

    if any(document.tenant_id != context.organization_id for document in request.rag_documents):
        raise HTTPException(status_code=403, detail="RAG document organization mismatch")
    report = runner.run(
        validation.blueprint,
        plan,
        request.cases,
        knowledge_documents=request.knowledge_documents,
        rag_documents=request.rag_documents,
        tenant_id=context.organization_id,
    )
    return BlueprintReleaseCheckResponse(
        evaluated=True,
        report=report,
        errors=[],
        warnings=warnings,
    )
