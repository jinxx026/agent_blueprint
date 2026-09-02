"""Blueprint Compiler composition and deterministic ExecutionPlan generation."""

import hashlib
import json

from app.blueprint.errors import IssueSeverity
from app.blueprint.schema import Blueprint
from app.blueprint.validator import BlueprintValidator
from app.compiler.diagnostics import CompilationDiagnostic, CompilationError
from app.compiler.graph_plan import GraphPlanBuilder
from app.compiler.instruction_builder import InstructionBuilder
from app.compiler.intermediate import (
    AgentSpec,
    ApprovalSpec,
    EvaluationPlan,
    ExecutionLimits,
    ExecutionPlan,
    PlanSource,
    ToolBindingSpec,
)
from app.compiler.policy_compiler import PolicyCompiler
from app.compiler.retriever_plan import RetrieverPlanBuilder


class BlueprintCompiler:
    """Compile a semantically valid Blueprint into a portable immutable plan."""

    def __init__(
        self,
        validator: BlueprintValidator | None = None,
        instruction_builder: InstructionBuilder | None = None,
        retriever_builder: RetrieverPlanBuilder | None = None,
        policy_compiler: PolicyCompiler | None = None,
        graph_builder: GraphPlanBuilder | None = None,
    ) -> None:
        self._validator = validator or BlueprintValidator()
        self._instruction_builder = instruction_builder or InstructionBuilder()
        self._retriever_builder = retriever_builder or RetrieverPlanBuilder()
        self._policy_compiler = policy_compiler or PolicyCompiler()
        self._graph_builder = graph_builder or GraphPlanBuilder()

    def compile(self, blueprint: Blueprint) -> ExecutionPlan:
        validation_errors = tuple(
            CompilationDiagnostic(issue.code, issue.path, issue.message)
            for issue in self._validator.validate(blueprint)
            if issue.severity is IssueSeverity.ERROR
        )
        if validation_errors:
            raise CompilationError(validation_errors)

        content_hash = self._content_hash(blueprint)
        assigned_agents_by_tool = {
            tool.id: tuple(agent.id for agent in blueprint.spec.agents if tool.id in agent.tools)
            for tool in blueprint.spec.tools
        }

        agents = tuple(
            AgentSpec(
                id=agent.id,
                display_name=agent.display_name,
                role=agent.role,
                goal=agent.goal,
                system_instruction=self._instruction_builder.build(blueprint, agent),
                knowledge_source_ids=tuple(agent.knowledge),
                tool_ids=tuple(agent.tools),
                delegate_to=tuple(agent.can_delegate_to),
            )
            for agent in blueprint.spec.agents
        )
        tools = tuple(
            ToolBindingSpec(
                id=tool.id,
                connector_ref=tool.connector_ref,
                operation=tool.operation,
                effect=tool.effect,
                risk=tool.risk,
                allowed_roles=tuple(tool.allowed_roles),
                assigned_agent_ids=assigned_agents_by_tool[tool.id],
                input_schema_json=json.dumps(
                    tool.input_schema,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                idempotency_required=tool.idempotency_required,
                approval_policy_id=tool.approval_policy,
            )
            for tool in blueprint.spec.tools
        )
        approvals = tuple(
            ApprovalSpec(
                id=approval.id,
                approver_roles=tuple(approval.approver_roles),
                expires_after=approval.expires_after,
                on_expire=approval.on_expire,
                require_reason=approval.require_reason,
            )
            for approval in blueprint.spec.approvals
        )
        runtime = blueprint.spec.runtime
        evaluation = blueprint.spec.evaluation

        return ExecutionPlan(
            schema_version="executionplan.agentblueprint.dev/v0.1",
            compiler_version="0.1.0",
            plan_id=(
                f"{blueprint.metadata.name}:{blueprint.metadata.version}:"
                f"compiler-0.1.0:{content_hash[:12]}"
            ),
            source=PlanSource(
                blueprint_name=blueprint.metadata.name,
                blueprint_version=blueprint.metadata.version,
                api_version=blueprint.api_version,
                content_hash=content_hash,
            ),
            agents=agents,
            retrievers=self._retriever_builder.build(blueprint),
            tools=tools,
            policies=self._policy_compiler.compile(blueprint),
            approvals=approvals,
            graph=self._graph_builder.build(blueprint),
            limits=ExecutionLimits(
                max_steps=runtime.max_steps,
                timeout_seconds=runtime.timeout_seconds,
                max_model_calls=runtime.max_model_calls,
                max_tool_calls=runtime.max_tool_calls,
                require_structured_output=runtime.require_structured_output,
            ),
            evaluation=EvaluationPlan(
                dataset_ref=evaluation.dataset_ref,
                minimum_score=evaluation.minimum_score,
                required_checks=tuple(evaluation.required_checks),
            ),
        )

    @staticmethod
    def _content_hash(blueprint: Blueprint) -> str:
        canonical = json.dumps(
            blueprint.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()
