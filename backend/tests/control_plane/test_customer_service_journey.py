"""End-to-end proof for the guided customer-service product journey."""

from pathlib import Path

from fastapi.testclient import TestClient


def _text_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, value in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + value + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return bytes(pdf)


def test_customer_service_journey(
    client: TestClient, auth_headers, example_blueprint_path: Path
) -> None:
    headers = auth_headers("journey-tenant")
    uploaded = client.post(
        "/api/v1/control/knowledge-documents/pdf",
        headers=headers,
        files={"file": ("after-sales.pdf", _text_pdf("Refund within 7 days."), "application/pdf")},
        data={
            "source_id": "after_sales_policy",
            "allowed_roles": "customer_service,supervisor",
            "citation_base": "knowledge://customer-service/after-sales-policy",
        },
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["page_count"] == 1

    saved = client.post(
        "/api/v1/control/blueprints",
        headers=headers,
        json={"content": example_blueprint_path.read_text(encoding="utf-8"), "format": "yaml"},
    )
    assert saved.status_code == 201, saved.text
    blueprint_id = saved.json()["id"]

    preview = client.post(
        f"/api/v1/control/blueprints/{blueprint_id}/execute",
        headers=headers,
        json={"message": "What is the refund policy?", "policy_context": {}},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["citations"]
    assert preview.json()["trace"]

    refund = client.post(
        f"/api/v1/control/blueprints/{blueprint_id}/execute",
        headers=headers,
        json={
            "message": "为订单 A100 创建 299 元退款",
            "policy_context": {"customer_identity_verified": True},
        },
    )
    assert refund.status_code == 200, refund.text
    assert refund.json()["status"] == "pending_approval"
    pending = refund.json()["pending_approvals"][0]
    resumed = client.post(
        f"/api/v1/executions/{refund.json()['thread_id']}/resume",
        headers=headers,
        json={
            "approval_id": pending["approval_id"],
            "decision": "approve",
            "reason": "verified by supervisor",
        },
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "completed"

    evaluation = client.post(
        f"/api/v1/control/blueprints/{blueprint_id}/evaluations",
        headers=headers,
        json={
            "use_stored_knowledge": True,
            "cases": [
                {
                    "id": "policy",
                    "description": "grounded policy answer",
                    "input": {"message": "Explain refund policy", "actor_role": "customer_service"},
                    "fixtures": {},
                    "expected": {
                        "outcome": "completed",
                        "forbidden_tools": ["create_refund_draft"],
                        "must_cite": ["after-sales-policy"],
                        "max_tool_calls": 0,
                    },
                }
            ],
        },
    )
    assert evaluation.status_code == 200, evaluation.text
    assert evaluation.json()["passed"] is True

    deployment = client.post(
        f"/api/v1/control/blueprints/{blueprint_id}/publish",
        headers=headers,
        json={"environment": "test"},
    )
    assert deployment.status_code == 200, deployment.text
    assert deployment.json()["endpoint"] == f"/api/v1/apps/{blueprint_id}/invoke"

    invoked = client.post(
        deployment.json()["endpoint"],
        headers=headers,
        json={"message": "Explain refund policy", "policy_context": {}},
    )
    assert invoked.status_code == 200, invoked.text
    assert invoked.json()["result"]["citations"]
