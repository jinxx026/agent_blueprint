# AgentBlueprint Frontend

企业 AI 智能体装配控制台，使用 React、Vinext 和 Tailwind CSS 构建。

## 页面职责

- `app/page.tsx`：业务向导、高级流程画布和测试控制台。
- `app/modules/page.tsx`：业务模块选择和每个模块的独立 RAG 配置。
- `app/blueprints/page.tsx`：Blueprint 编辑、保存和版本历史。
- `app/knowledge/page.tsx`：企业知识录入、角色授权和索引状态。
- `app/evaluations/page.tsx`：自动评测和发布门禁。
- `app/security/page.tsx`：当前组织、用户、角色和安全底座。
- `app/settings/page.tsx`：后端地址与访问令牌。
- `components/canvas-workspace.tsx`：可拖拽节点和可平移视野的流程画布。
- `components/studio-shell.tsx`：管理页面的导航、身份和连接状态。
- `lib/agentblueprint-api.ts`：统一 API 类型、认证头和请求方法。

## 本地启动

建议从仓库根目录运行 `scripts/dev.ps1` 或 `scripts/dev.sh`。单独启动时：

```powershell
npm ci
npm run dev
```

默认连接 `http://127.0.0.1:8000/api/v1`，可以通过 `.env.local` 中的 `NEXT_PUBLIC_AGENTBLUEPRINT_API_URL` 修改。

线上环境必须使用 HTTPS 后端；模型和企业系统密钥只能保存在后端。
