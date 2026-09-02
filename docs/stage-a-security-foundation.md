# 阶段 A：企业安全底座

状态：进行中  
最后更新：2026-09-02

## A1 身份与租户边界（已完成）

- JWT HS256 与企业 OIDC/JWKS 验证。
- 服务端 `RequestContext`。
- Organization、User、Role、Membership 基础数据表。
- Membership 角色作为最终权限来源。
- 控制面、RAG 运行和人工审批不再信任客户端自报身份。
- 生产环境禁止 development 认证。
- 越权、令牌篡改和租户伪造测试。

## A2 PostgreSQL 与迁移（下一步）

- 将 SQLite 控制面迁移到 PostgreSQL。
- 引入版本化数据库迁移。
- 为所有企业数据增加 `organization_id` 外键和索引。
- 使用 PostgreSQL Row Level Security 提供第二道租户隔离。
- 增加 Docker Compose 中的 PostgreSQL 服务。

## A3 LangGraph 持久化（待实施）

- 使用 PostgreSQL Checkpointer 替换 `InMemorySaver`。
- 持久化 Run、RunEvent、ApprovalRequest 和 ExecutionPlan 引用。
- 服务重启后重建图并恢复等待审批的任务。

## A4 权限管理与前端登录（待实施）

- 管理员邀请成员、分配角色、停用 Membership。
- 前端登录回调、Session Provider、401/403 页面。
- 业务负责人、AI 开发者、审批人和审计员的页面权限。

## 当前安全性质

本阶段已修复“客户端可以伪造 tenant_id 和 approver_roles”的问题，但在 A2/A3 完成前，SQLite 和内存 Checkpointer 仍只适合本地开发，不能标记为生产就绪。
