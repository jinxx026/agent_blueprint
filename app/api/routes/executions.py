"""Resume LangGraph executions paused for human approval."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_blueprint_executor, get_request_context
from app.governance.approvals import (
    ApprovalAuthorizationError,
    ApprovalExpiredError,
    ApprovalResume,
)
from app.identity import RequestContext
from app.runtime import BlueprintExecutor
from app.runtime.executor import ExecutionResult
from app.schemas.blueprint import ApprovalResumeRequest

router = APIRouter()


@router.post(
    "/{thread_id}/resume",
    response_model=ExecutionResult,
    summary="Approve or reject a paused Blueprint execution",
)
def resume_execution(
    thread_id: str,
    request: ApprovalResumeRequest,
    executor: Annotated[BlueprintExecutor, Depends(get_blueprint_executor)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> ExecutionResult:
    try:
        decision = ApprovalResume(
            approval_id=request.approval_id,
            decision=request.decision,
            reason=request.reason,
            approver_roles=context.roles,
        )
        return executor.resume(thread_id, decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ApprovalExpiredError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
