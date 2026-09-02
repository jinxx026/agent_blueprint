"""Run evaluation cases and make a deterministic release decision."""

import json

from app.blueprint.schema import Blueprint, EvaluationCheck
from app.compiler.intermediate import ExecutionPlan
from app.evaluation.models import (
    CheckResult,
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationObservation,
    EvaluationOutcome,
    ReleaseGateReport,
)
from app.rag import RagDocument, RagKnowledgeStore, create_local_rag_pipeline
from app.runtime import BlueprintExecutor, KnowledgeDocument, MemoryKnowledgeStore
from app.runtime.executor import ExecutionResult, ExecutionStatus

SAFETY_CHECKS = {
    EvaluationCheck.AUTHORIZATION,
    EvaluationCheck.APPROVAL_BEHAVIOR,
}


class EvaluationRunner:
    """Execute every case independently and enforce the Blueprint's gate."""

    def __init__(self, executor: BlueprintExecutor) -> None:
        self._executor = executor

    def run(
        self,
        blueprint: Blueprint,
        plan: ExecutionPlan,
        cases: tuple[EvaluationCase, ...],
        *,
        knowledge_documents: tuple[KnowledgeDocument, ...] = (),
        rag_documents: tuple[RagDocument, ...] = (),
        tenant_id: str = "default",
    ) -> ReleaseGateReport:
        pipeline = None
        if rag_documents:
            pipeline = create_local_rag_pipeline()
            pipeline.ingest(rag_documents)

        results = tuple(
            self._run_case(
                blueprint,
                plan,
                case,
                index,
                knowledge_documents,
                pipeline,
                tenant_id,
            )
            for index, case in enumerate(cases)
        )
        all_checks = tuple(check for case in results for check in case.checks)
        score = sum(check.passed for check in all_checks) / len(all_checks) if all_checks else 0.0
        blockers = []
        if score < plan.evaluation.minimum_score:
            blockers.append(
                f"score {score:.3f} is below minimum {plan.evaluation.minimum_score:.3f}"
            )
        for case in results:
            for check in case.checks:
                if check.check in SAFETY_CHECKS and not check.passed:
                    blockers.append(f"{case.case_id}: required safety check {check.check} failed")
        return ReleaseGateReport(
            plan_id=plan.plan_id,
            dataset_ref=plan.evaluation.dataset_ref,
            score=round(score, 4),
            minimum_score=plan.evaluation.minimum_score,
            passed=not blockers,
            blockers=tuple(dict.fromkeys(blockers)),
            cases=results,
        )

    def _run_case(
        self,
        blueprint: Blueprint,
        plan: ExecutionPlan,
        case: EvaluationCase,
        index: int,
        knowledge_documents: tuple[KnowledgeDocument, ...],
        pipeline: object | None,
        tenant_id: str,
    ) -> EvaluationCaseResult:
        roles = (case.input.actor_role,)
        authorized = bool(set(roles).intersection(blueprint.spec.audience.allowed_roles))
        if not authorized:
            observation = EvaluationObservation(outcome=EvaluationOutcome.DENIED)
        else:
            try:
                knowledge = (
                    RagKnowledgeStore(pipeline, tenant_id=tenant_id, roles=frozenset(roles))
                    if pipeline is not None
                    else MemoryKnowledgeStore(knowledge_documents)
                )
                result = self._executor.execute(
                    plan,
                    case.input.message,
                    f"eval-{plan.source.content_hash[:8]}-{index}-{case.id}",
                    policy_context=case.fixtures,
                    actor_roles=roles,
                    knowledge=knowledge,
                )
                observation = self._observe(result)
            except Exception as exc:  # each failed case must still produce a report
                observation = EvaluationObservation(
                    outcome=EvaluationOutcome.ERROR,
                    error=f"{type(exc).__name__}: {exc}",
                )

        checks = tuple(
            self._check(check, case, observation, authorized)
            for check in plan.evaluation.required_checks
        )
        score = sum(check.passed for check in checks) / len(checks) if checks else 0.0
        return EvaluationCaseResult(
            case_id=case.id,
            description=case.description,
            passed=all(check.passed for check in checks),
            score=round(score, 4),
            checks=checks,
            observation=observation,
        )

    @staticmethod
    def _observe(result: ExecutionResult) -> EvaluationObservation:
        tool_calls = tuple(tool for report in result.reports for tool in report.tool_calls)
        pending_tools = tuple(approval.tool_id for approval in result.pending_approvals)
        approver_roles = tuple(
            dict.fromkeys(
                role for approval in result.pending_approvals for role in approval.approver_roles
            )
        )
        outcome = (
            EvaluationOutcome.WAITING_APPROVAL
            if result.status is ExecutionStatus.PENDING_APPROVAL
            else EvaluationRunner._completed_outcome(result)
        )
        return EvaluationObservation(
            outcome=outcome,
            answer=result.answer,
            citations=result.citations,
            tool_calls=tool_calls,
            pending_tool_ids=pending_tools,
            approver_roles=approver_roles,
            model_calls=result.model_calls,
        )

    @staticmethod
    def _completed_outcome(result: ExecutionResult) -> EvaluationOutcome:
        for report in result.reports:
            for raw in report.tool_results:
                try:
                    payload = json.loads(raw)
                except (TypeError, json.JSONDecodeError):
                    continue
                if payload.get("reason") == "transfer_to_human":
                    return EvaluationOutcome.TRANSFERRED_TO_HUMAN
                if payload.get("status") == "denied":
                    return EvaluationOutcome.DENIED
        return EvaluationOutcome.COMPLETED

    @staticmethod
    def _check(
        check: EvaluationCheck,
        case: EvaluationCase,
        actual: EvaluationObservation,
        authorized: bool,
    ) -> CheckResult:
        expected = case.expected
        if check is EvaluationCheck.FINAL_ANSWER:
            outcome_ok = actual.outcome is expected.outcome
            content_ok = all(
                fragment in (actual.answer or "") for fragment in expected.answer_contains
            )
            passed = outcome_ok and content_ok
            message = f"expected outcome={expected.outcome}, actual={actual.outcome}"
        elif check is EvaluationCheck.CITATIONS:
            missing = tuple(
                fragment
                for fragment in expected.must_cite
                if not any(fragment in citation for citation in actual.citations)
            )
            passed = not missing
            message = "all required citations found" if passed else f"missing citations: {missing}"
        elif check is EvaluationCheck.TOOL_TRAJECTORY:
            seen = set(actual.tool_calls + actual.pending_tool_ids)
            missing = set(expected.required_tools) - seen
            forbidden = set(expected.forbidden_tools).intersection(seen)
            limits_ok = (
                expected.max_tool_calls is None or len(actual.tool_calls) <= expected.max_tool_calls
            ) and (
                expected.max_model_calls is None or actual.model_calls <= expected.max_model_calls
            )
            passed = not missing and not forbidden and limits_ok
            message = (
                f"seen={sorted(seen)}, missing={sorted(missing)}, forbidden={sorted(forbidden)}"
            )
        elif check is EvaluationCheck.AUTHORIZATION:
            passed = authorized or expected.outcome is EvaluationOutcome.DENIED
            message = (
                f"actor authorized={authorized}; unauthorized actors must expect a denied outcome"
            )
        else:
            has_approval = bool(actual.pending_tool_ids)
            tool_ok = (
                expected.requested_tool is None
                or expected.requested_tool in actual.pending_tool_ids
            )
            role_ok = (
                expected.approver_role is None or expected.approver_role in actual.approver_roles
            )
            passed = has_approval is expected.approval_required and tool_ok and role_ok
            message = (
                f"approval={has_approval}, pending_tools={actual.pending_tool_ids}, "
                f"approver_roles={actual.approver_roles}"
            )
        return CheckResult(check=check, passed=passed, message=message)
