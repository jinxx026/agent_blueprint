export const SAMPLE_BLUEPRINT = `api_version: agentblueprint.dev/v0.1
kind: AgentBlueprint
metadata:
  name: customer-refund-assistant
  display_name: 售后退款助理
  version: 0.1.0
  description: 依据售后政策为客服生成退款建议
  labels:
    department: customer-service
spec:
  identity:
    role: 售后退款助理
    goal: 基于有效政策给出可追溯的退款建议
    responsibilities:
      - 检索退款政策并解释适用条款
    prohibited_actions:
      - 不得绕过权限和人工审批
    success_definition:
      - 所有政策结论都有引用
  audience:
    allowed_roles: [customer_service, supervisor]
    default_language: zh-CN
  knowledge:
    - id: after_sales_policy
      type: documents
      description: 当前有效的退换货政策
      source_ref: knowledge://customer-service/after-sales-policy
      allowed_roles: [customer_service, supervisor]
      citation_required: true
      freshness: 24h
  rag:
    enabled: true
    strategy: agentic
    default_top_k: 6
    rerank: true
    return_citations: true
  tools: []
  agents:
    - id: supervisor
      display_name: 售后协调Agent
      role: 理解任务、分派工作并汇总
      goal: 协调退款处理
      knowledge: []
      tools: []
      can_delegate_to: [policy-specialist, order-specialist, refund-specialist]
    - id: policy-specialist
      display_name: 售后政策Agent
      role: 检索并解释当前政策
      goal: 返回包含引用的政策结论
      knowledge: [after_sales_policy]
      tools: []
      can_delegate_to: []
    - id: order-specialist
      display_name: 订单核验Agent
      role: 核验订单事实
      goal: 返回最小必要订单信息
      knowledge: []
      tools: []
      can_delegate_to: []
    - id: refund-specialist
      display_name: 退款执行Agent
      role: 生成退款处理建议
      goal: 根据政策输出退款建议
      knowledge: [after_sales_policy]
      tools: []
      can_delegate_to: []
  orchestration:
    framework: langgraph
    pattern: supervisor
    entry_agent: supervisor
    parallel_delegation: false
    human_in_the_loop: true
  policies: []
  approvals: []
  fallback:
    missing_information: ask_user
    conflicting_knowledge: transfer_to_human
    tool_failure:
      action: retry
      max_attempts: 2
    unsafe_request: deny
  runtime:
    max_steps: 12
    timeout_seconds: 120
    max_model_calls: 8
    max_tool_calls: 5
    require_structured_output: true
  evaluation:
    dataset_ref: ./eval-cases.jsonl
    minimum_score: 0.9
    required_checks: [final_answer, citations, authorization, approval_behavior]
`;
