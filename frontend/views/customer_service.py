"""Guided after-sales AI assembly and verification workspace."""

from pathlib import Path

import streamlit as st
from api_client import ApiClient, ApiError

BLUEPRINT_PATH = (
    Path(__file__).resolve().parents[2] / "examples" / "customer-support" / "blueprint.yaml"
)


def _blueprint(client: ApiClient) -> dict[str, object] | None:
    records = client.get("/control/blueprints")
    return next((item for item in records if item["name"] == "customer-refund-assistant"), None)


def _show_execution(result: dict[str, object]) -> None:
    status = result.get("status")
    if status == "pending_approval":
        st.warning("退款草稿已暂停，正在等待主管审批。")
    else:
        st.success("处理完成")
    if result.get("answer"):
        st.markdown(str(result["answer"]))

    citations = result.get("citations", [])
    with st.expander(f"引用依据 · {len(citations)} 条", expanded=bool(citations)):
        if citations:
            for citation in citations:
                st.code(str(citation), language=None)
        else:
            st.caption("本次回答没有产生知识库引用。")

    reports = result.get("reports", [])
    with st.expander(f"Agent 协作轨迹 · {len(reports)} 个报告", expanded=True):
        for report in reports:
            st.markdown(f"**{report.get('agent_id', 'Agent')}**")
            st.write(report.get("content", ""))
            if report.get("tool_results"):
                st.caption("工具结果")
                st.json(report["tool_results"])
        st.caption(" → ".join(str(item) for item in result.get("trace", [])))


def render(client: ApiClient) -> None:
    st.markdown(
        """
        <div class="hero"><div class="eyebrow">CUSTOMER SERVICE WORKSPACE</div>
        <h1>售后客服 AI 装配线</h1>
        <p>上传企业政策后，系统自动建立可追溯知识库、生成多 Agent 工作流，
        并通过审批和评测门禁发布成 API。</p></div>
        """,
        unsafe_allow_html=True,
    )

    steps = st.columns(4)
    for column, number, title in zip(
        steps,
        ("01", "02", "03", "04"),
        ("上传政策", "生成应用", "对话验证", "评测发布"),
        strict=True,
    ):
        column.markdown(f"**{number} · {title}**")

    st.subheader("1. 上传售后政策 PDF")
    st.caption("系统只提取文字；扫描版 PDF 需要先 OCR。单文件最大 10 MB、300 页。")
    uploaded = st.file_uploader("选择企业售后政策", type=["pdf"], key="cs_policy_pdf")
    if st.button("解析并写入 RAG 知识库", type="primary", disabled=uploaded is None):
        try:
            response = client.upload_pdf(
                "/control/knowledge-documents/pdf",
                uploaded.name,
                uploaded.getvalue(),
                {
                    "source_id": "after_sales_policy",
                    "allowed_roles": "customer_service,supervisor",
                    "citation_base": "knowledge://customer-service/after-sales-policy",
                },
            )
            st.session_state.cs_document = response
            st.success(
                f"已解析 {response['page_count']} 页、{response['character_count']} 个字符。"
            )
        except ApiError as exc:
            st.error(str(exc))

    if st.session_state.get("cs_document"):
        with st.expander("查看入库结果"):
            st.json(st.session_state.cs_document)

    st.divider()
    st.subheader("2. 自动生成客服 Blueprint")
    st.caption("装配政策 Agent、订单 Agent、退款 Agent，以及 RAG、权限和主管审批规则。")
    if st.button("安装客服模块并生成 Blueprint"):
        try:
            client.put(
                "/control/modules/customer-support",
                {
                    "rag": {
                        "strategy": "hybrid",
                        "chunk_strategy": "contextual",
                        "chunk_size": 800,
                        "chunk_overlap": 120,
                        "candidate_count": 20,
                        "top_k": 5,
                        "rerank": True,
                        "compression": True,
                        "return_citations": True,
                        "source_ids": ["after_sales_policy"],
                    }
                },
            )
            record = client.post(
                "/control/blueprints",
                {"content": BLUEPRINT_PATH.read_text(encoding="utf-8"), "format": "yaml"},
            )
            st.session_state.cs_blueprint = record
            st.success("客服 Blueprint 已生成并保存。")
        except (ApiError, OSError) as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("3. 在线提问并查看执行证据")
    st.caption("试试政策问题；或输入“为订单 A100 创建 299 元退款”查看主管审批。")
    question = st.text_input("客户问题", value="这份政策规定的退款条件是什么？")
    if st.button("运行客服 Agent", type="primary"):
        try:
            record = st.session_state.get("cs_blueprint") or _blueprint(client)
            if not record:
                st.warning("请先生成客服 Blueprint。")
            else:
                response = client.post(
                    f"/control/blueprints/{record['id']}/execute",
                    {
                        "message": question,
                        "policy_context": {"customer_identity_verified": True},
                    },
                )
                st.session_state.cs_last_result = response
        except ApiError as exc:
            st.error(str(exc))

    result = st.session_state.get("cs_last_result")
    if result:
        _show_execution(result)
        approvals = result.get("pending_approvals", [])
        if approvals:
            approval = approvals[0]
            reason = st.text_input("审批意见", value="信息与金额已核验，同意创建退款草稿")
            approve, deny = st.columns(2)
            decision = "approve" if approve.button("主管批准", type="primary") else None
            if deny.button("主管拒绝"):
                decision = "reject"
            if decision:
                try:
                    resumed = client.post(
                        f"/executions/{result['thread_id']}/resume",
                        {
                            "approval_id": approval["approval_id"],
                            "decision": decision,
                            "reason": reason,
                        },
                    )
                    st.session_state.cs_last_result = resumed
                    st.rerun()
                except ApiError as exc:
                    st.error(str(exc))

    st.divider()
    st.subheader("4. 自动评测并发布 API")
    blueprint = st.session_state.get("cs_blueprint")
    if not blueprint:
        try:
            blueprint = _blueprint(client)
        except ApiError:
            blueprint = None
    run_eval, publish = st.columns(2)
    if run_eval.button("运行自动门禁", disabled=blueprint is None):
        try:
            evaluation = client.post(
                f"/control/blueprints/{blueprint['id']}/evaluations",
                {
                    "use_stored_knowledge": True,
                    "cases": [
                        {
                            "id": "policy-answer",
                            "description": "政策问答必须完成并引用售后政策",
                            "input": {"message": "解释退款政策", "actor_role": "customer_service"},
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
            st.session_state.cs_evaluation = evaluation
            if evaluation["passed"]:
                st.success(f"门禁通过 · 得分 {evaluation['score']:.0%}")
            else:
                st.error("门禁未通过，请展开结果检查阻断项。")
                st.json(evaluation["report"])
        except ApiError as exc:
            st.error(str(exc))
    if publish.button(
        "发布测试 API", disabled=not st.session_state.get("cs_evaluation", {}).get("passed")
    ):
        try:
            deployment = client.post(
                f"/control/blueprints/{blueprint['id']}/publish", {"environment": "test"}
            )
            st.session_state.cs_deployment = deployment
            st.success("发布完成。现在可以从本页面或外部系统调用。")
        except ApiError as exc:
            st.error(str(exc))
    if st.session_state.get("cs_deployment"):
        deployment = st.session_state.cs_deployment
        st.code(f"POST {deployment['endpoint']}", language="http")
        st.json({"message": "这份政策规定的退款条件是什么？", "policy_context": {}})
