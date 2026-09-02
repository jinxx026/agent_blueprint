"""Policy boundary for validated, retryable, idempotent connector calls."""

import hashlib
import json
import time
from collections.abc import Callable, Mapping
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from app.compiler.intermediate import ToolBindingSpec
from app.connectors.audit import AuditStatus, MemoryAuditSink
from app.connectors.contracts import ConnectorRequest
from app.connectors.errors import (
    ApprovalRequiredError,
    ConnectorInputError,
    ConnectorTemporaryError,
)
from app.connectors.registry import ConnectorRegistry


class ManagedToolExecutor:
    """The only production path from an agent to an enterprise connector."""

    def __init__(
        self,
        registry: ConnectorRegistry,
        audit: MemoryAuditSink | None = None,
        *,
        max_attempts: int = 3,
        sleep: Callable[[float], None] = time.sleep,
        approvals_enabled: bool = False,
    ) -> None:
        self._registry = registry
        self._audit = audit or MemoryAuditSink()
        self._max_attempts = max_attempts
        self._sleep = sleep
        self._approvals_enabled = approvals_enabled
        self._idempotency_cache: dict[str, str] = {}

    @property
    def audit(self) -> MemoryAuditSink:
        return self._audit

    def execute(
        self,
        spec: ToolBindingSpec,
        arguments: Mapping[str, Any],
        *,
        agent_id: str = "unknown-agent",
        execution_id: str = "unknown-execution",
        policy_context: Mapping[str, Any] | None = None,
        actor_roles: tuple[str, ...] = (),
        approval_granted: bool = False,
    ) -> str:
        self._validate_arguments(spec, arguments)
        if spec.approval_policy_id and not (self._approvals_enabled or approval_granted):
            raise ApprovalRequiredError(
                f"Tool '{spec.id}' requires approval policy '{spec.approval_policy_id}'"
            )

        idempotency_key = self._idempotency_key(spec, arguments, execution_id)
        argument_names = tuple(sorted(arguments))
        if idempotency_key and idempotency_key in self._idempotency_cache:
            self._record(
                spec, execution_id, agent_id, argument_names, AuditStatus.REUSED, attempts=0
            )
            return self._idempotency_cache[idempotency_key]

        connector = self._registry.resolve(spec.connector_ref)
        attempts = 0
        try:
            while True:
                attempts += 1
                try:
                    response = connector.invoke(
                        ConnectorRequest(
                            operation=spec.operation,
                            arguments=dict(arguments),
                            idempotency_key=idempotency_key,
                        )
                    )
                    result = json.dumps(response.data, ensure_ascii=False, default=str)
                    if idempotency_key:
                        self._idempotency_cache[idempotency_key] = result
                    self._record(
                        spec,
                        execution_id,
                        agent_id,
                        argument_names,
                        AuditStatus.SUCCEEDED,
                        attempts,
                    )
                    return result
                except ConnectorTemporaryError:
                    if attempts >= self._max_attempts:
                        raise
                    self._sleep(0.05 * (2 ** (attempts - 1)))
        except Exception as exc:
            self._record(
                spec,
                execution_id,
                agent_id,
                argument_names,
                AuditStatus.FAILED,
                attempts,
                type(exc).__name__,
            )
            raise

    @staticmethod
    def _validate_arguments(spec: ToolBindingSpec, arguments: Mapping[str, Any]) -> None:
        schema = json.loads(spec.input_schema_json)
        try:
            Draft202012Validator(schema).validate(dict(arguments))
        except ValidationError as exc:
            path = ".".join(str(part) for part in exc.absolute_path) or "$"
            raise ConnectorInputError(
                f"Invalid arguments for tool '{spec.id}' at '{path}': {exc.message}"
            ) from exc

    @staticmethod
    def _idempotency_key(
        spec: ToolBindingSpec, arguments: Mapping[str, Any], execution_id: str
    ) -> str | None:
        if not spec.idempotency_required:
            return None
        canonical = json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)
        raw = f"{execution_id}:{spec.id}:{canonical}".encode()
        return hashlib.sha256(raw).hexdigest()

    def _record(
        self,
        spec: ToolBindingSpec,
        execution_id: str,
        agent_id: str,
        argument_names: tuple[str, ...],
        status: AuditStatus,
        attempts: int,
        error_type: str | None = None,
    ) -> None:
        self._audit.record(
            execution_id=execution_id,
            agent_id=agent_id,
            tool_id=spec.id,
            connector_ref=spec.connector_ref,
            operation=spec.operation,
            argument_names=argument_names,
            status=status,
            attempts=attempts,
            error_type=error_type,
        )
