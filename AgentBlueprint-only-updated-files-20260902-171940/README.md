# AgentBlueprint

AgentBlueprint 是一个面向企业的 AI 智能体装配平台。企业选择业务模块，绑定自己的知识库和系统，再通过 Blueprint 编译、LangGraph 多 Agent Runtime、RAG、权限、人工审批与发布门禁形成可治理的 AI 应用。

项目不是单个聊天 Demo，而是一个前后端统一的 monorepo：

```text
企业配置业务模块与 RAG
          ↓
Blueprint Compiler 生成安全执行计划
          ↓
LangGraph Runtime 调度 Agent、知识和工具
          ↓
Policy / Approval / Evaluation 控制执行与发布
```

## 已实现能力

- 业务模块目录：客服、合同审查、HR、销售、财务审核和运营 SOP。
- 模块独立 RAG：上下文增强切片、混合召回、rerank、上下文压缩和引用。
- Blueprint：YAML 加载、结构校验、语义校验、版本和确定性编译。
- 多 Agent：LangChain 抽象和 LangGraph 编排。
- 企业治理：JWT/OIDC 身份、组织隔离、角色权限、工具网关和人工审批。
- 质量控制：自动评测、发布门禁、版本记录和审计数据。
- Streamlit 企业控制台：业务模块、RAG 配置、知识库、Blueprint、评测发布和安全设置。

当前 SQLite、内存索引和本地模型适配器适合开发验证。生产环境仍需切换 PostgreSQL、持久向量库、对象存储、模型网关和正式 OIDC/SSO。

## 仓库结构

```text
AgentBlueprint/
├── backend/                 FastAPI API、编译器、RAG 和 LangGraph Runtime
│   ├── app/                 后端业务代码
│   ├── tests/               端到端和单元测试
│   ├── pyproject.toml       Python 依赖与质量工具配置
│   └── .env.example         后端环境变量示例
├── frontend/                Streamlit 企业控制台
│   ├── app.py               前端入口、导航和全局样式
│   ├── api_client.py        FastAPI 请求与错误处理
│   ├── views/               模块、知识、蓝图、评测和安全页面
│   └── .streamlit/          非敏感主题设置
├── examples/                可运行的蓝图和评测案例
├── docs/                    架构、规范和决策记录
├── scripts/                 一键安装、启动和检查脚本
├── .gitignore               Git 排除规则
└── .gitattributes           跨平台换行规则
```

## 快速开始

环境要求：Python 3.11+。前后端共用 Python 环境，不需要 Node.js。

Windows PowerShell：

```powershell
.\scripts\setup.ps1
.\scripts\dev.ps1
```

macOS / Linux：

```bash
chmod +x scripts/*.sh
./scripts/setup.sh
./scripts/dev.sh
```

启动后访问：

- 前端控制台：http://localhost:8501
- 后端 API：http://127.0.0.1:8000/api/v1
- API 文档：http://127.0.0.1:8000/docs

## 运行检查

Windows：

```powershell
.\scripts\check.ps1
```

macOS / Linux：

```bash
./scripts/check.sh
```

## Streamlit Cloud 部署

在 Streamlit Community Cloud 中把主文件设置为 `frontend/app.py`，Python 版本选择 3.12。平台会读取 `frontend/requirements.txt` 安装前端依赖，并读取仓库根目录的 `.streamlit/config.toml`。

云端前端无法访问你电脑上的 `127.0.0.1:8000`。先把 FastAPI 部署到可访问的 HTTPS 地址，再在 Streamlit 应用 Secrets 中配置：

```toml
API_BASE_URL = "https://你的后端域名/api/v1"
```

## 安全约束

- 企业组织、用户和角色只来自后端验证后的 RequestContext。
- 前端不能指定或修改租户身份。
- 模型密钥、数据库密码和连接器凭证不进入 Blueprint 或浏览器代码。
- RAG 文档按组织、知识源和允许角色过滤。
- 高风险工具需要确定性 Policy 与人工审批，不能交给模型自行决定。

## 上传 GitHub

交付压缩包已经排除 `.git`、`.venv`、残留依赖目录、构建缓存、本地数据库和环境密钥。解压后可以直接作为新仓库根目录：

```bash
git init
git add .
git commit -m "Initial AgentBlueprint platform"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

更详细的设计见 `docs/architecture.md`、`docs/enterprise-platform-design.md` 和 `docs/blueprint-spec.md`。
