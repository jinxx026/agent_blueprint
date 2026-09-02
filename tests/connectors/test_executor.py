from pathlib import Path

import pytest

from app.blueprint.loader import BlueprintFormat
from app.blueprint.service import BlueprintService
from app.compiler import BlueprintCompiler
from app.connectors import ConnectorRegistry, FunctionConnector, ManagedToolExecutor
from app.connectors.contracts import ConnectorRequest, ConnectorResponse
from app.connectors.errors import (
    ApprovalRequiredError,
    ConnectorInputError,
    ConnectorTemporaryError,
)


def compile_tools(path: Path):
    result = BlueprintService().validate_text(
        path.read_text(encoding="utf-8"), BlueprintFormat.YAML
    )
    assert result.blueprint is not None
    return {tool.id: tool for tool in BlueprintCompiler().compile(result.blueprint).tools}


def test_gateway_validates_arguments_before_calling_connector(
    example_blueprint_path: Path,
) -> None:
    tools = compile_tools(example_blueprint_path)
    registry = ConnectorRegistry(
        {
            "connector://commerce/orders": FunctionConnector(
                {"get_order": lambda arguments: {"id": arguments["order_id"]}}
            )
        }
    )

    with pytest.raises(ConnectorInputError, match="order_id"):
        ManagedToolExecutor(registry).execute(tools["get_order"], {})


def test_approval_bound_write_is_blocked_until_approval_runtime_exists(
    example_blueprint_path: Path,
) -> None:
    tools = compile_tools(example_blueprint_path)

    with pytest.raises(ApprovalRequiredError, match="requires approval"):
        ManagedToolExecutor(ConnectorRegistry()).execute(
            tools["create_refund_draft"],
            {"order_id": "O-1", "amount": 20, "reason": "customer request"},
        )


def test_idempotent_write_runs_once_and_audit_never_stores_argument_values(
    example_blueprint_path: Path,
) -> None:
    tools = compile_tools(example_blueprint_path)
    calls = 0

    def create_draft(arguments: dict[str, object]) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"draft_id": "D-1", "order_id": arguments["order_id"]}

    registry = ConnectorRegistry(
        {"connector://commerce/refunds": FunctionConnector({"create_refund_draft": create_draft})}
    )
    executor = ManagedToolExecutor(registry, approvals_enabled=True)
    arguments = {"order_id": "O-SECRET", "amount": 20, "reason": "customer request"}

    first = executor.execute(
        tools["create_refund_draft"],
        arguments,
        agent_id="refund-specialist",
        execution_id="run-1",
    )
    second = executor.execute(
        tools["create_refund_draft"],
        arguments,
        agent_id="refund-specialist",
        execution_id="run-1",
    )

    assert first == second
    assert calls == 1
    assert [record.status for record in executor.audit.records] == ["succeeded", "reused"]
    assert executor.audit.records[0].argument_names == ("amount", "order_id", "reason")
    assert "O-SECRET" not in executor.audit.records[0].model_dump_json()


class FlakyConnector:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, request: ConnectorRequest) -> ConnectorResponse:
        self.calls += 1
        if self.calls < 3:
            raise ConnectorTemporaryError("temporary")
        return ConnectorResponse(data={"order_id": request.arguments["order_id"]})


def test_gateway_retries_only_temporary_connector_failures(
    example_blueprint_path: Path,
) -> None:
    tools = compile_tools(example_blueprint_path)
    connector = FlakyConnector()
    delays: list[float] = []
    executor = ManagedToolExecutor(
        ConnectorRegistry({"connector://commerce/orders": connector}),
        max_attempts=3,
        sleep=delays.append,
    )

    result = executor.execute(tools["get_order"], {"order_id": "O-1"})

    assert '"order_id": "O-1"' in result
    assert connector.calls == 3
    assert delays == [0.05, 0.1]
    assert executor.audit.records[0].attempts == 3
