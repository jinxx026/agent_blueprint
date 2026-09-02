# AgentBlueprint Specification v0.1

状态：Draft  
格式：YAML 或 JSON  
字符编码：UTF-8

## 1. 规范目标

Blueprint 是企业与系统之间的业务契约。它描述智能体必须遵守的事实、能力和限制，但不描述具体模型 SDK、数据库表结构或界面布局。

同一份 Blueprint 应能：

- 通过网页向导创建。
- 作为 YAML/JSON 进入版本控制。
- 编译到不同模型适配器。
- 生成评测和治理配置。
- 在开发、测试和生产环境之间晋级。

## 2. 顶层结构

```yaml
api_version: agentblueprint.dev/v0.1
kind: AgentBlueprint
metadata: {}
spec:
  identity: {}
  audience: {}
  knowledge: []
  rag: {}
  tools: []
  agents: []
  orchestration: {}
  policies: []
  approvals: []
  fallback: {}
  runtime: {}
  evaluation: {}
```

未知顶层字段默认视为错误，防止拼写错误被静默忽略。

## 3. metadata

| 字段 | 类型 | 必填 | 含义 |
|---|---|---:|---|
| `name` | string | 是 | 机器可读名称，使用小写字母、数字和连字符 |
| `display_name` | string | 是 | 用户可见名称 |
| `version` | string | 是 | 语义化版本 |
| `description` | string | 是 | 简洁描述业务目的 |
| `labels` | map | 否 | 用于分类和检索，不影响行为 |

`metadata.version` 描述业务蓝图版本；编译器还会计算内容哈希，二者用途不同。

## 4. spec.identity

定义智能体作为一个企业岗位的职责边界。

| 字段 | 类型 | 必填 | 含义 |
|---|---|---:|---|
| `role` | string | 是 | 岗位名称 |
| `goal` | string | 是 | 可验证的主要目标 |
| `responsibilities` | string[] | 是 | 应执行的职责 |
| `prohibited_actions` | string[] | 是 | 明确禁止的行为 |
| `success_definition` | string[] | 是 | 业务成功条件 |

Compiler 会根据这些业务字段生成模型指令，但原字段始终保留用于审计。

## 5. spec.audience

定义谁可以使用智能体，以及默认对话语言。

```yaml
audience:
  allowed_roles: [customer_service, supervisor]
  default_language: zh-CN
```

`allowed_roles` 为空属于错误，因为没有可合法使用该智能体的主体。

## 6. spec.knowledge

每项知识源包含：

| 字段 | 类型 | 必填 | 含义 |
|---|---|---:|---|
| `id` | string | 是 | Blueprint 内唯一标识 |
| `type` | enum | 是 | `documents`、`database` 或 `api` |
| `description` | string | 是 | 内容和用途 |
| `source_ref` | string | 是 | 外部配置引用，不是密钥 |
| `allowed_roles` | string[] | 是 | 可检索此知识的角色 |
| `citation_required` | boolean | 是 | 输出是否必须提供引用 |
| `freshness` | string | 否 | 数据最大可接受陈旧时间，如 `24h` |

知识访问权限不能超过智能体受众范围。

### 6.1 spec.rag

定义企业知识如何进入模型上下文：

```yaml
rag:
  enabled: true
  strategy: agentic
  default_top_k: 6
  rerank: true
  return_citations: true
```

`strategy` 支持：

- `two_step`：先检索再生成，延迟和轨迹更确定。
- `agentic`：Agent根据任务决定何时及如何检索。
- `hybrid`：先执行固定检索，再允许Agent按需补充检索。

Blueprint只描述RAG语义；Compiler将在后续阶段把知识源编译为LangChain Retriever和LangGraph节点。

### 6.2 spec.agents

每个Agent定义独立职责和最小上下文：

```yaml
- id: policy-specialist
  display_name: 售后政策专家
  role: 只分析政策适用范围
  goal: 返回有引用的政策结论
  knowledge: [after_sales_policy]
  tools: []
  can_delegate_to: []
```

Agent只能看到显式分配的知识和工具。`can_delegate_to`声明允许的协作边，不能形成循环。

### 6.3 spec.orchestration

```yaml
orchestration:
  framework: langgraph
  pattern: supervisor
  entry_agent: supervisor
  parallel_delegation: true
  human_in_the_loop: true
```

`pattern` 支持 `single`、`supervisor`、`router`、`handoff` 和 `custom`。v1默认使用 `supervisor`：主Agent维护用户上下文，把专业任务作为工具委派给无状态子Agent；审批和可恢复状态由LangGraph管理。

## 7. spec.tools

每个工具描述模型可以请求的受控能力：

| 字段 | 类型 | 必填 | 含义 |
|---|---|---:|---|
| `id` | string | 是 | Blueprint 内唯一工具名 |
| `description` | string | 是 | 何时使用及其效果 |
| `connector_ref` | string | 是 | 已注册连接器引用 |
| `operation` | string | 是 | 连接器中的操作名 |
| `effect` | enum | 是 | `read`、`write` 或 `irreversible` |
| `risk` | enum | 是 | `low`、`medium`、`high`、`critical` |
| `allowed_roles` | string[] | 是 | 可请求此工具的角色 |
| `input_schema` | object | 是 | JSON Schema 参数定义 |
| `idempotency_required` | boolean | 是 | 写操作是否要求幂等键 |
| `approval_policy` | string/null | 是 | 审批策略 ID |

静态规则：

- `write` 工具必须设置 `idempotency_required: true`。
- `irreversible` 工具在 v1 中不允许启用。
- `high` 或 `critical` 风险工具必须引用审批策略。
- `read` 工具也必须执行角色和租户校验。

## 8. spec.policies

Policy 表达可确定执行的业务规则：

```yaml
- id: refund-amount-policy
  description: 按退款金额决定处理方式
  applies_to: [draft_refund]
  rules:
    - when: amount <= 500
      decision: allow
    - when: amount > 500
      decision: require_approval
```

`when` 在 v0.1 只允许受限表达式，禁止执行任意脚本。Policy 的结果为：

- `allow`
- `deny`
- `require_approval`
- `transfer_to_human`

## 9. spec.approvals

审批策略定义谁可以批准什么：

```yaml
- id: supervisor-refund-approval
  approver_roles: [supervisor]
  expires_after: 24h
  on_expire: deny
  require_reason: true
```

审批人不能仅依赖模型生成的摘要，还必须能看到工具、参数、数据依据和匹配到的规则。

## 10. spec.fallback

定义可预测的异常处理：

```yaml
fallback:
  missing_information: ask_user
  conflicting_knowledge: transfer_to_human
  tool_failure:
    action: retry
    max_attempts: 2
  unsafe_request: deny
```

允许的主要动作包括 `ask_user`、`retry`、`deny`、`transfer_to_human` 和 `stop`。

## 11. spec.runtime

限制一次运行的资源和自主程度：

```yaml
runtime:
  max_steps: 12
  timeout_seconds: 120
  max_model_calls: 8
  max_tool_calls: 5
  require_structured_output: true
```

这些限制由 Runtime 强制执行，不能只写进模型指令。

## 12. spec.evaluation

```yaml
evaluation:
  dataset_ref: ./eval-cases.jsonl
  minimum_score: 0.90
  required_checks:
    - final_answer
    - citations
    - tool_trajectory
    - authorization
    - approval_behavior
```

发布条件：总分达到 `minimum_score`，并且所有安全类检查通过。安全类失败不能被其他高分抵消。

## 13. 评测案例格式

每行是一个独立 JSON 对象，至少包含：

```json
{
  "id": "refund-under-limit",
  "input": {"message": "...", "actor_role": "customer_service"},
  "expected": {
    "outcome": "completed",
    "required_tools": ["get_order"],
    "forbidden_tools": [],
    "approval_required": false,
    "must_cite": ["after_sales_policy"]
  }
}
```

JSONL 便于流式读取、逐案例追加和在大型数据集中定位错误。

## 14. 版本兼容性

- `api_version` 发生变化代表规范兼容边界变化。
- `metadata.version` 由业务创建者管理。
- 编译器必须明确声明支持的 `api_version`。
- 不支持的版本必须拒绝，不能尝试猜测字段含义。
- 将来提供显式迁移命令，不在加载阶段静默迁移。
