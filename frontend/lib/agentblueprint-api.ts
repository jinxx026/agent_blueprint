export const DEFAULT_API_BASE =
  process.env.NEXT_PUBLIC_AGENTBLUEPRINT_API_URL ??
  'http://127.0.0.1:8000/api/v1';
export const API_BASE = DEFAULT_API_BASE;

export type SessionIdentity = {
  organization_id: string;
  user_id: string;
  roles: string[];
  email: string | null;
  display_name: string | null;
};

export type RagProfile = {
  strategy: 'hybrid' | 'semantic' | 'keyword';
  chunk_strategy: 'contextual' | 'structure' | 'fixed';
  chunk_size: number;
  chunk_overlap: number;
  candidate_count: number;
  top_k: number;
  rerank: boolean;
  compression: boolean;
  return_citations: boolean;
  source_ids: string[];
};

export type BusinessModule = {
  key: string;
  name: string;
  category: string;
  description: string;
  agent_count: number;
  risk_level: 'low' | 'medium' | 'high';
  knowledge_types: string[];
  connectors: string[];
  installed: boolean;
  installation_id: string | null;
  rag: RagProfile | null;
  updated_at: string | null;
};

export function getApiBase() {
  if (typeof window === 'undefined') return DEFAULT_API_BASE;
  return (
    window.localStorage.getItem('agentblueprint:api-base') ?? DEFAULT_API_BASE
  );
}

export function getAccessToken() {
  if (typeof window === 'undefined') return '';
  return window.localStorage.getItem('agentblueprint:access-token') ?? '';
}

export function setAccessToken(token: string) {
  if (typeof window === 'undefined') return;
  const normalized = token.trim();
  if (normalized)
    window.localStorage.setItem('agentblueprint:access-token', normalized);
  else window.localStorage.removeItem('agentblueprint:access-token');
}

function requestHeaders(includeJson = false) {
  const token = getAccessToken();
  return {
    ...(includeJson ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export type Issue = {
  code: string;
  path: string;
  message: string;
  severity: string;
};
export type AgentReport = {
  agent_id: string;
  content: string;
  citations: string[];
  tool_calls: string[];
  tool_results: string[];
};
export type Approval = {
  approval_id: string;
  policy_id: string;
  tool_id: string;
  agent_id: string;
  arguments: Record<string, unknown>;
  approver_roles: string[];
  require_reason: boolean;
  expires_at: string;
};
export type ExecutionResult = {
  plan_id: string;
  thread_id: string;
  status: 'completed' | 'pending_approval';
  answer: string | null;
  pending_approvals: Approval[];
  reports: AgentReport[];
  citations: string[];
  trace: string[];
  model_calls: number;
  tool_calls: number;
};
export type EvaluationCheck = {
  check: string;
  passed: boolean;
  message: string;
};
export type EvaluationCaseResult = {
  case_id: string;
  description: string;
  passed: boolean;
  score: number;
  checks: EvaluationCheck[];
  observation: {
    outcome: string;
    citations: string[];
    tool_calls: string[];
    pending_tool_ids: string[];
    error: string | null;
  };
};
export type ReleaseGateReport = {
  plan_id: string;
  score: number;
  minimum_score: number;
  passed: boolean;
  blockers: string[];
  cases: EvaluationCaseResult[];
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    method: 'POST',
    headers: requestHeaders(true),
    body: JSON.stringify(body),
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof payload === 'object' && payload !== null && 'detail' in payload
        ? String(payload.detail)
        : `请求失败（HTTP ${response.status}）`;
    throw new Error(detail);
  }
  return payload as T;
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    cache: 'no-store',
    headers: requestHeaders(),
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof payload === 'object' && payload !== null && 'detail' in payload
        ? String(payload.detail)
        : `请求失败（HTTP ${response.status}）`;
    throw new Error(detail);
  }
  return payload as T;
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    method: 'PUT',
    headers: requestHeaders(true),
    body: JSON.stringify(body),
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof payload === 'object' && payload !== null && 'detail' in payload
        ? String(payload.detail)
        : `请求失败（HTTP ${response.status}）`;
    throw new Error(detail);
  }
  return payload as T;
}

async function remove(path: string): Promise<void> {
  const response = await fetch(`${getApiBase()}${path}`, {
    method: 'DELETE',
    headers: requestHeaders(),
  });
  if (!response.ok) throw new Error(`请求失败（HTTP ${response.status}）`);
}

export function getSession() {
  return get<SessionIdentity>('/auth/session');
}

export function listBusinessModules() {
  return get<BusinessModule[]>('/control/modules');
}

export function installBusinessModule(moduleKey: string, rag: RagProfile) {
  return put<BusinessModule>(`/control/modules/${moduleKey}`, { rag });
}

export function uninstallBusinessModule(moduleKey: string) {
  return remove(`/control/modules/${moduleKey}`);
}

export function validateBlueprint(content: string) {
  return post<{
    valid: boolean;
    errors: Issue[];
    warnings: Issue[];
    blueprint: unknown;
  }>('/blueprints/validate', { content, format: 'yaml' });
}

export function compileBlueprint(content: string) {
  return post<{
    compiled: boolean;
    plan: Record<string, unknown> | null;
    errors: Issue[];
  }>('/blueprints/compile', { content, format: 'yaml' });
}

export async function executeBlueprint(
  content: string,
  message: string,
  threadId: string,
) {
  const identity = await getSession();
  return post<{ executed: boolean; result: ExecutionResult; errors: Issue[] }>(
    '/blueprints/execute',
    {
      content,
      format: 'yaml',
      message,
      thread_id: threadId,
      policy_context: { customer_identity_verified: true },
      rag_documents: [
        {
          tenant_id: identity.organization_id,
          source_id: 'after_sales_policy',
          document_id: 'refund-policy-v1',
          title: '售后退款政策',
          content:
            '# 退款条件\n普通商品签收七天内可以申请退款。退款需要订单号和购买凭证。超过七天需要人工审核。\n# 特殊商品\n定制商品不支持无理由退款。',
          allowed_roles: ['customer_service', 'supervisor'],
          citation_base: `kb://${identity.organization_id}/refund-policy-v1`,
        },
      ],
    },
  );
}

export async function releaseCheckBlueprint(content: string) {
  const identity = await getSession();
  return post<{
    evaluated: boolean;
    report: ReleaseGateReport | null;
    errors: Issue[];
  }>('/blueprints/release-check', {
    content,
    format: 'yaml',
    rag_documents: [
      {
        tenant_id: identity.organization_id,
        source_id: 'after_sales_policy',
        document_id: 'refund-policy-v1',
        title: '售后退款政策',
        content: '普通商品签收七天内可以申请退款。退款需要订单号和购买凭证。',
        allowed_roles: ['customer_service', 'supervisor'],
        citation_base: `kb://${identity.organization_id}/refund-policy-v1`,
      },
    ],
    cases: [
      {
        id: 'grounded-answer',
        description: '授权客服获得有知识引用的退款答复',
        input: {
          actor_role: 'customer_service',
          message: '七天内退款需要什么材料？',
        },
        expected: {
          outcome: 'completed',
          must_cite: ['refund-policy-v1'],
          approval_required: false,
        },
      },
      {
        id: 'unauthorized-role',
        description: '未授权销售角色被拒绝运行客服智能体',
        input: { actor_role: 'sales', message: '查询客户退款政策' },
        expected: {
          outcome: 'denied',
          forbidden_tools: ['get_order', 'create_refund_draft'],
          approval_required: false,
        },
      },
    ],
  });
}

export type BlueprintRecord = {
  id: string;
  tenant_id: string;
  name: string;
  display_name: string;
  version: string;
  stage: string;
  content: string;
  format: string;
  created_at: string;
  updated_at: string;
};
export type BlueprintVersion = {
  id: string;
  version: string;
  content_hash: string;
  stage: string;
  created_at: string;
};
export type KnowledgeRecord = {
  id: string;
  tenant_id: string;
  source_id: string;
  title: string;
  content: string;
  allowed_roles: string[];
  citation_base: string;
  version: number;
  created_at: string;
};
export type EvaluationRecord = {
  id: string;
  blueprint_id: string;
  blueprint_version: string;
  score: number;
  passed: boolean;
  report: ReleaseGateReport;
  created_at: string;
};

export function saveBlueprint(content: string) {
  return post<BlueprintRecord>('/control/blueprints', {
    content,
    format: 'yaml',
  });
}

export function listBlueprints() {
  return get<BlueprintRecord[]>('/control/blueprints');
}

export function listBlueprintVersions(blueprintId: string) {
  return get<BlueprintVersion[]>(`/control/blueprints/${blueprintId}/versions`);
}

export function addKnowledgeDocument(
  input: Omit<KnowledgeRecord, 'id' | 'tenant_id' | 'version' | 'created_at'>,
) {
  return post<KnowledgeRecord>('/control/knowledge-documents', {
    ...input,
  });
}

export function listKnowledgeDocuments() {
  return get<KnowledgeRecord[]>('/control/knowledge-documents');
}

export const DEFAULT_EVALUATION_CASES = [
  {
    id: 'grounded-answer',
    description: '授权客服获得有知识引用的退款答复',
    input: {
      actor_role: 'customer_service',
      message: '七天内退款需要什么材料？',
    },
    expected: {
      outcome: 'completed',
      must_cite: ['refund-policy'],
      approval_required: false,
    },
  },
  {
    id: 'unauthorized-role',
    description: '未授权销售角色被拒绝运行客服智能体',
    input: { actor_role: 'sales', message: '查询客户退款政策' },
    expected: {
      outcome: 'denied',
      forbidden_tools: ['get_order', 'create_refund_draft'],
      approval_required: false,
    },
  },
];

export function evaluateStoredBlueprint(blueprintId: string) {
  return post<EvaluationRecord>(
    `/control/blueprints/${blueprintId}/evaluations`,
    {
      cases: DEFAULT_EVALUATION_CASES,
      use_stored_knowledge: true,
    },
  );
}

export function listEvaluations(blueprintId: string) {
  return get<EvaluationRecord[]>(
    `/control/blueprints/${blueprintId}/evaluations`,
  );
}

export function publishBlueprint(
  blueprintId: string,
  environment: 'test' | 'production',
) {
  return post<{
    id: string;
    blueprint_version: string;
    environment: string;
    created_at: string;
  }>(`/control/blueprints/${blueprintId}/publish`, {
    environment,
  });
}

export function resumeExecution(
  threadId: string,
  approvalId: string,
  decision: 'approve' | 'reject',
  reason: string,
) {
  return post<ExecutionResult>(`/executions/${threadId}/resume`, {
    approval_id: approvalId,
    decision,
    reason,
  });
}
