from pathlib import Path

from app.blueprint.loader import BlueprintFormat
from app.blueprint.schema import PolicyDecision
from app.blueprint.service import BlueprintService
from app.compiler import BlueprintCompiler
from app.governance import PolicyEngine


def compile_plan(path: Path):
    result = BlueprintService().validate_text(
        path.read_text(encoding="utf-8"), BlueprintFormat.YAML
    )
    assert result.blueprint is not None
    return BlueprintCompiler().compile(result.blueprint)


def test_policy_engine_combines_rules_with_fail_closed_precedence(
    example_blueprint_path: Path,
) -> None:
    plan = compile_plan(example_blueprint_path)
    engine = PolicyEngine()

    approval = engine.evaluate(
        plan,
        "create_refund_draft",
        {"customer_identity_verified": True, "amount": 100},
    )
    denied = engine.evaluate(plan, "create_refund_draft", {"amount": 100})
    transferred = engine.evaluate(
        plan,
        "create_refund_draft",
        {"customer_identity_verified": True, "amount": 6000},
    )

    assert approval.decision is PolicyDecision.REQUIRE_APPROVAL
    assert denied.decision is PolicyDecision.DENY
    assert "verified-identity-required" in denied.unmatched_policy_ids
    assert transferred.decision is PolicyDecision.TRANSFER_TO_HUMAN
