from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient


def save_example(
    client: TestClient,
    path: Path,
    headers: dict[str, str] | None = None,
    tenant_id: str = "forged-client-value",
) -> dict:
    response = client.post(
        "/api/v1/control/blueprints",
        json={
            "tenant_id": tenant_id,
            "content": path.read_text(encoding="utf-8"),
            "format": "yaml",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_blueprints_are_saved_versioned_and_tenant_isolated(
    client: TestClient,
    example_blueprint_path: Path,
    auth_headers: Callable[[str, tuple[str, ...]], dict[str, str]],
) -> None:
    acme_headers = auth_headers("acme")
    other_headers = auth_headers("other")
    saved = save_example(client, example_blueprint_path, acme_headers)

    acme = client.get(
        "/api/v1/control/blueprints",
        params={"tenant_id": "other"},
        headers=acme_headers,
    )
    other = client.get("/api/v1/control/blueprints", headers=other_headers)
    versions = client.get(
        f"/api/v1/control/blueprints/{saved['id']}/versions",
        params={"tenant_id": "other"},
        headers=acme_headers,
    )

    assert [item["id"] for item in acme.json()] == [saved["id"]]
    assert other.json() == []
    assert versions.json()[0]["version"] == "0.1.0"


def test_passing_evaluation_is_required_before_publish(
    client: TestClient,
    example_blueprint_path: Path,
    auth_headers: Callable[[str, tuple[str, ...]], dict[str, str]],
) -> None:
    headers = auth_headers("acme")
    saved = save_example(client, example_blueprint_path, headers)
    blocked = client.post(
        f"/api/v1/control/blueprints/{saved['id']}/publish",
        json={"tenant_id": "acme", "environment": "production"},
        headers=headers,
    )
    assert blocked.status_code == 409

    document = client.post(
        "/api/v1/control/knowledge-documents",
        json={
            "tenant_id": "acme",
            "source_id": "after_sales_policy",
            "title": "退款政策",
            "content": "普通商品七天内可以退款，需要订单号。",
            "allowed_roles": ["customer_service"],
            "citation_base": "kb://acme/refund-policy",
        },
        headers=headers,
    )
    assert document.status_code == 201

    evaluated = client.post(
        f"/api/v1/control/blueprints/{saved['id']}/evaluations",
        json={
            "tenant_id": "acme",
            "cases": [
                {
                    "id": "grounded",
                    "description": "授权客服获得有引用的答案",
                    "input": {
                        "actor_role": "customer_service",
                        "message": "退款需要什么？",
                    },
                    "expected": {
                        "outcome": "completed",
                        "must_cite": ["refund-policy"],
                        "approval_required": False,
                    },
                }
            ],
        },
        headers=headers,
    )
    assert evaluated.status_code == 200
    assert evaluated.json()["passed"] is True

    published = client.post(
        f"/api/v1/control/blueprints/{saved['id']}/publish",
        json={"tenant_id": "acme", "environment": "production"},
        headers=headers,
    )
    assert published.status_code == 200
    assert published.json()["blueprint_version"] == "0.1.0"


def test_knowledge_documents_are_tenant_isolated(
    client: TestClient,
    auth_headers: Callable[[str, tuple[str, ...]], dict[str, str]],
) -> None:
    acme_headers = auth_headers("acme")
    other_headers = auth_headers("other")
    client.post(
        "/api/v1/control/knowledge-documents",
        json={
            "tenant_id": "acme",
            "source_id": "handbook",
            "title": "员工手册",
            "content": "请假需要提前申请。",
            "allowed_roles": ["employee"],
            "citation_base": "kb://acme/handbook",
        },
        headers=acme_headers,
    )

    assert len(client.get("/api/v1/control/knowledge-documents", headers=acme_headers).json()) == 1
    assert (
        client.get(
            "/api/v1/control/knowledge-documents",
            params={"tenant_id": "acme"},
            headers=other_headers,
        ).json()
        == []
    )


def test_business_modules_are_installed_with_tenant_scoped_rag_profiles(
    client: TestClient,
    auth_headers: Callable[[str, tuple[str, ...]], dict[str, str]],
) -> None:
    acme_headers = auth_headers("acme", ("organization_admin",))
    other_headers = auth_headers("other", ("organization_admin",))
    installed = client.put(
        "/api/v1/control/modules/contract-review",
        json={
            "tenant_id": "forged-company",
            "rag": {
                "strategy": "hybrid",
                "chunk_strategy": "contextual",
                "chunk_size": 900,
                "chunk_overlap": 120,
                "candidate_count": 30,
                "top_k": 6,
                "rerank": True,
                "compression": True,
                "return_citations": True,
                "source_ids": ["contracts", "legal-rules"],
            },
        },
        headers=acme_headers,
    )

    assert installed.status_code == 200
    assert installed.json()["installed"] is True
    assert installed.json()["rag"]["chunk_size"] == 900
    acme_catalog = client.get("/api/v1/control/modules", headers=acme_headers).json()
    other_catalog = client.get("/api/v1/control/modules", headers=other_headers).json()
    assert next(item for item in acme_catalog if item["key"] == "contract-review")["installed"]
    assert not next(item for item in other_catalog if item["key"] == "contract-review")["installed"]


def test_business_module_changes_require_administration_role(
    client: TestClient,
    auth_headers: Callable[[str, tuple[str, ...]], dict[str, str]],
) -> None:
    response = client.put(
        "/api/v1/control/modules/customer-service",
        json={"rag": {}},
        headers=auth_headers("acme", ("customer_service",)),
    )
    assert response.status_code == 403
