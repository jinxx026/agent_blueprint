# AgentBlueprint Backend

后端目前提供 Blueprint 校验、确定性编译，以及 LangChain/LangGraph 多 Agent 执行 Runtime。

## 本地开发

在 `backend` 目录运行：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ui]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

服务启动后：

- 健康检查：`GET http://127.0.0.1:8000/api/v1/health`
- Blueprint 校验：`POST http://127.0.0.1:8000/api/v1/blueprints/validate`
- Blueprint 编译：`POST http://127.0.0.1:8000/api/v1/blueprints/compile`
- Blueprint 执行：`POST http://127.0.0.1:8000/api/v1/blueprints/execute`
- 自动评测与发布门禁：`POST http://127.0.0.1:8000/api/v1/blueprints/release-check`
- 蓝图版本仓库：`/api/v1/control/blueprints`
- 企业知识文档：`/api/v1/control/knowledge-documents`
- 业务模块与独立 RAG 配置：`/api/v1/control/modules`
- 持久评测与发布：`/api/v1/control/blueprints/{id}/evaluations`、`/publish`
- 审批后恢复：`POST http://127.0.0.1:8000/api/v1/executions/{thread_id}/resume`
- API 文档：`http://127.0.0.1:8000/docs`

仓库根目录的 `scripts/dev.ps1` 会同时启动 FastAPI 和 Streamlit 企业控制台；前端地址是 `http://localhost:8501`。

### 企业身份

- `GET /api/v1/auth/session`：返回服务端验证后的组织、用户和角色。
- `POST /api/v1/auth/development-token`：仅本地开发模式可用，用于测试不同组织身份。
- `development` 模式无令牌时使用固定 demo 身份；生产必须配置 `jwt` 或 `oidc`。

业务 API 中的组织和角色来自 `RequestContext`。为了兼容旧客户端，请求模型暂时仍可携带 `tenant_id`、`user_roles` 或 `approver_roles`，但后端会忽略这些字段。

运行质量检查：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
```

## 包边界

- `app.main`：组装应用，不实现业务逻辑。
- `app.core`：全局基础能力，目前包含配置。
- `app.identity`：JWT/OIDC 验证、服务端 RequestContext 和组织身份边界。
- `app.api`：HTTP 路由与请求级依赖。
- `app.blueprint`：框架无关的 Blueprint 领域模型、解析和语义校验。
- `app.compiler`：把合法 Blueprint 编译为不可变、可序列化的 ExecutionPlan。
- `app.runtime`：把 ExecutionPlan 变成 LangGraph，并连接模型、RAG 和工具适配器。
- `app.connectors`：企业工具网关，负责认证、参数校验、重试、幂等和安全审计。
- `app.rag`：上下文增强切片、Embedding、混合索引、rerank、上下文压缩和权限过滤。
- `app.governance`：确定性 Policy 求值、工具角色授权、LangGraph 人工审批和审批审计。
- `app.evaluation`：运行验收用例，检查答案、引用、工具、权限和审批，并生成发布门禁报告。
- `app.storage`：持久化租户蓝图、不可变版本、知识文档、评测报告和发布记录。
- `app.modules`：平台业务模块模板目录，企业安装记录由控制面按组织保存。
- `app.schemas`：API 输入输出数据契约。
- `tests`：从外部行为验证应用。

## Blueprint校验示例

接口只接受内联内容，不接受服务器文件路径：

```json
{
  "content": "api_version: agentblueprint.dev/v0.1\nkind: AgentBlueprint\n...",
  "format": "yaml"
}
```

Loader使用安全YAML解析并拒绝重复键；Schema检查字段类型；Validator检查Agent、知识、工具、审批和委派图之间的关系。

`/blueprints/compile` 在相同校验之后返回完整ExecutionPlan。该接口不会运行模型或企业工具。

`/blueprints/execute` 会继续构建并运行 LangGraph。可通过 `knowledge_documents` 使用简单内存知识，也可通过 `rag_documents`、`tenant_id` 和 `user_roles` 启用完整的上下文增强 RAG，包括混合召回、权限过滤、rerank、上下文压缩和引用追踪。当前 Embedding 与 reranker 为无需 API Key 的本地实现，可由生产适配器替换。

`/blueprints/release-check` 会先校验和编译 Blueprint，再用真实 Runtime 独立运行每条内联评测用例。总分低于 Blueprint 的 `minimum_score` 会阻断发布；权限或审批安全项失败时，无论平均分多少都会阻断。`dataset_ref` 目前只作为版本引用记录，接口不会按照用户输入读取服务器文件。
