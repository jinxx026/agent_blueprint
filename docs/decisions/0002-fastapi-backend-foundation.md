# ADR-0002：FastAPI后端基础与应用工厂

状态：Accepted  
日期：2026-08-30

## 背景

Compiler、Runtime、治理和评测模块都需要稳定的HTTP入口、类型校验和配置系统。开发测试还需要在同一个Python进程中创建相互隔离的应用实例。

## 决策

后端采用FastAPI和Pydantic Settings，并使用 `create_app(settings)` 应用工厂组装应用。

包依赖方向为：

```text
API routes → application services → domain/core interfaces
main.py     → 只负责组装
schemas     → 定义HTTP数据契约
```

当前阶段尚未创建application和domain包；它们会在Blueprint与Compiler实现时加入。API路由不得直接实现Compiler或Runtime业务逻辑。

## 原因

1. FastAPI原生使用Python类型生成请求校验和OpenAPI文档。
2. Pydantic Settings可以统一验证环境变量，避免在业务代码中散落字符串读取。
3. 应用工厂允许测试显式注入配置，不依赖开发机器的 `.env`。
4. Router组合可以让后续Blueprint、Runs、Approvals等接口独立演进。

## 关键约束

- `app.main`是Composition Root，只组装对象和路由。
- 配置对象创建后不可修改。
- 环境变量统一使用 `AGENTBLUEPRINT_` 前缀。
- API从 `/api/v1` 开始版本化。
- API输入输出必须使用显式Schema。
- Secret不得出现在健康接口、日志或Blueprint中。

## 后果

正面影响：应用易于测试、接口可生成文档、配置错误可以在启动时暴露。

需要承担：业务逻辑增加后必须持续维护依赖方向，防止路由直接操作数据库或调用模型。
