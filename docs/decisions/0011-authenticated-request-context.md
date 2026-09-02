# ADR 0011：由认证身份生成 RequestContext

状态：Accepted  
日期：2026-09-02

## 背景

旧控制面 API 接受前端提交的 `tenant_id` 和角色。如果攻击者修改请求，就可能冒充其他企业或审批角色。仅在 SQL 中加入租户条件不能解决问题，因为租户条件本身仍来自不可信客户端。

## 决定

API 边界统一验证 Bearer Token，并生成不可变 `RequestContext`：

```text
Authorization: Bearer <token>
→ 验证签名、issuer、audience、exp
→ 读取 organization_id 与 subject
→ 查询平台 Membership
→ 使用数据库中的角色
→ RequestContext
```

- 业务路由只能从 `RequestContext` 读取组织和角色。
- 请求中的旧 `tenant_id`、`user_roles` 和 `approver_roles` 仅暂时兼容客户端，不参与授权。
- 本地开发允许无令牌使用固定 demo 身份，并提供本地令牌签发端点。
- 生产环境禁止 development 模式。
- OIDC 模式通过企业 IdP 的 JWKS 验证 RS256/ES256 Token。

## 结果

伪造正文、查询参数或审批角色不会改变服务端身份。后续 PostgreSQL 行级安全仍使用同一个 `organization_id`，形成应用层和数据库层双重隔离。
