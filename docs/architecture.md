# AgentBlueprint 总体架构

状态：Accepted  
对应规范：Blueprint v0.1

> 企业平台的目标分层、安全不变量、部署拓扑和实施顺序以
> [enterprise-platform-design.md](./enterprise-platform-design.md) 为准。本文件保留各核心模块的详细设计。

## 1. 架构目标

系统必须把业务描述、编译决策和运行行为分开，使每一层都能独立验证：

- Blueprint 层表达企业想要什么。
- Compiler 层决定如何转换为执行结构。
- Runtime 层负责安全地执行。
- Control Plane 管理版本、权限、评测和发布。
- Data Plane 处理每一次实际的模型、检索与工具调用。

## 2. 系统上下文

```text
业务负责人 ──配置──┐
开发者 ──YAML/API─┼→ AgentBlueprint
管理员 ──治理─────┤       │
审批人 ──审批─────┘       ├→ 模型提供方
                           ├→ 企业知识源
终端用户 ──请求───────────┤→ 企业业务 API
                           └→ 审计与监控系统
```

AgentBlueprint 不拥有企业原始业务系统，而是在授权范围内读取数据或请求操作。

## 3. 核心模块

### 3.1 Authoring

提供网页向导和 YAML/JSON API。它只负责收集业务事实，不直接拼接最终 Prompt。

输入：岗位、用户、知识、工具、规则、审批、限制和评测要求。  
输出：符合 Blueprint Schema 的版本化文档。

### 3.2 Blueprint Loader 与 Validator

Loader 负责解析格式；Validator 负责两类检查：

1. 结构检查：字段类型、必填项、枚举和格式。
2. 语义检查：工具引用是否存在、高风险操作是否审批、角色是否有对应授权。

输出是经过校验的 Blueprint，而不是运行时对象。

### 3.3 Compiler

Compiler 将 Blueprint 转换为规范化中间表示和不可变执行计划：

```text
Blueprint
  → normalize
  → static analysis
  → policy expansion
  → instruction generation
  → ExecutionPlan
```

执行计划包含模型指令、可见知识、Retriever规格、工具绑定、已解析策略、图节点与边、限制和终止条件。编译结果带内容哈希，用于版本追踪和缓存。

Compiler禁止直接生成LangChain或LangGraph对象，先输出 `ExecutionPlan v0.1`：

```text
Blueprint
  ├─ AgentDefinition       → AgentSpec
  ├─ RAG + Knowledge       → RetrieverSpec
  ├─ ToolDefinition        → ToolBindingSpec
  ├─ PolicyRule.when       → ConditionSpec
  ├─ ApprovalPolicy        → ApprovalSpec
  └─ Orchestration         → GraphPlan
```

同一Blueprint必须生成相同SHA-256内容哈希和Plan ID。部署时间等环境状态不进入编译结果。

### 3.4 Runtime

Runtime 使用事件驱动状态机执行计划：

```text
CREATED → RUNNING → WAITING_APPROVAL → RUNNING → COMPLETED
                    ↘ REJECTED
RUNNING → FAILED / CANCELLED / LIMIT_REACHED
```

每次状态改变都会产生事件，运行状态可通过事件重建。这使暂停审批、服务重启和事后审计成为可能。

### 3.5 Model Gateway

统一不同模型提供方的消息、结构化输出、工具调用、用量和错误格式。业务模块不得直接依赖某一家模型 SDK。

### 3.6 Knowledge Service

负责文档摄取、分段、向量化、检索、重排和引用。返回的不只是文本，还必须包含：

- 组织和知识源标识
- 文档与版本标识
- 片段位置
- 检索分数
- 访问权限标签

### 3.7 Tool Registry 与 Executor

Registry 保存工具定义；Executor 执行工具。执行前依次进行：

```text
参数校验 → 身份与租户检查 → 角色权限 → 风险策略 → 审批状态 → 实际调用
```

模型只能提出工具调用请求，不能绕过 Executor 直接访问外部系统。

### 3.8 Governance

包含策略引擎、风险分类、人工审批、审计和安全护栏。业务金额阈值等确定性规则由策略引擎执行，不依赖模型自然语言判断。

### 3.9 Evaluation

评测引擎可以用固定输入运行某个 Blueprint 版本，并检查最终输出和完整轨迹。发布服务只接受达到最低分数的版本。

### 3.10 LangChain、RAG与多Agent

最终运行架构采用分层组合：

```text
Blueprint Compiler
  ↓ 生成图定义、Agent规格和Retriever规格
LangGraph StateGraph
  ├─ Supervisor Agent（LangChain create_agent）
  ├─ Policy Specialist
  ├─ Order Specialist
  ├─ Refund Specialist
  ├─ RAG Retriever节点
  └─ Approval Interrupt节点
```

- LangChain负责模型适配、工具、Retriever、文档对象和单Agent工具调用循环。
- LangGraph负责共享State、节点、条件边、持久化、并行分派和人工审批。
- RAG知识源先经过加载、分段、Embedding和Vector Store，再以Retriever或Agent工具暴露。
- Supervisor只向子Agent传递完成任务所需的最小上下文，避免企业全部资料进入同一上下文窗口。
- 确定性权限和审批仍在Tool Executor与Policy Engine执行，不能委托给LangChain Agent自行决定。

## 4. Control Plane 与 Data Plane

### Control Plane

管理低频、持久的控制信息：

- 组织、用户和角色
- Blueprint 及版本
- 知识源与工具定义
- 策略和评测集
- 测试、发布与回滚

### Data Plane

执行高频请求：

- 创建一次 Run
- 调用模型
- 检索知识
- 请求和执行工具
- 等待审批
- 写入事件与用量

分离两者可以让发布配置保持稳定，同时让运行任务独立扩缩容。

## 5. 关键数据对象

- `Organization`：租户安全边界。
- `User` / `Role`：身份和权限主体。
- `Blueprint` / `BlueprintVersion`：业务配置及不可变版本。
- `ExecutionPlan`：编译产物。
- `AgentDeployment`：某环境当前发布的版本。
- `Run`：一次端到端执行。
- `RunEvent`：模型、检索、工具、审批和状态事件。
- `ApprovalRequest`：高风险操作的暂停点。
- `EvaluationSuite` / `EvaluationRun`：验收集和运行结果。

## 6. 一次请求的数据流

1. API 验证用户身份和组织。
2. Deployment 找到当前发布的 ExecutionPlan。
3. Runtime 创建 Run 和初始事件。
4. Model Gateway 请求模型给出结构化下一步。
5. 若需要知识，Knowledge Service 在组织和权限范围内检索。
6. 若需要工具，Executor 完成所有策略检查。
7. 需要审批时持久化状态并暂停，不占用工作进程。
8. 审批后从事件状态恢复。
9. 结束时保存结果、引用、用量和完整轨迹。

## 7. 安全边界

- Blueprint 不存储任何真实密钥，只引用 Secret ID。
- 每个数据查询必须携带 Organization ID。
- 工具调用在服务端重新校验参数和权限。
- 模型输出永远被视为不可信输入。
- 检索文档中的指令不自动获得系统指令权限。
- 写操作使用幂等键，避免重试造成重复副作用。
- 审计事件记录行为事实，但对敏感字段进行脱敏。

## 8. 计划技术栈

- Web：React、TypeScript。
- API：Python、FastAPI、Pydantic。
- 数据库：PostgreSQL，向量检索使用 pgvector。
- 异步任务：Redis 与任务队列。
- 对象存储：S3 兼容存储。
- Agent框架：LangChain。
- 编排与持久运行：LangGraph。
- 可观测性：OpenTelemetry；后续允许接入LangSmith，但不作为自托管运行的强依赖。
- 部署：Docker Compose 起步，保持未来容器编排兼容性。

具体依赖在实现前以 ADR 记录，避免设计文档被某个库的短期接口绑死。

## 9. 仓库边界

项目采用单仓库，计划结构如下：

```text
AgentBlueprint/
├─ backend/          API、Compiler、Runtime 和服务端测试
├─ frontend/         企业配置与管理界面
├─ docs/             产品、规范、架构和ADR
├─ examples/         可运行模板和评测数据
├─ deploy/           本地与私有部署配置
└─ .github/workflows 持续集成
```

阶段 0 只创建 `docs` 和 `examples`，其他目录在对应阶段出现，保证每个文件都有当前用途。
