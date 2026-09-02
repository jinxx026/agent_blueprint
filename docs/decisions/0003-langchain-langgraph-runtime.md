# ADR-0003：采用LangChain组件与LangGraph多Agent运行时

状态：Accepted  
日期：2026-08-31

## 背景

AgentBlueprint需要支持企业RAG、工具调用、长任务、人工审批和多Agent协作。普通顺序Chain不足以表达暂停恢复、条件分支、并行子任务和持久状态。

## 决策

采用以下分工：

- LangChain：模型、消息、工具、Retriever和单Agent抽象。
- LangGraph：StateGraph、多Agent拓扑、持久化、流式事件和human-in-the-loop。
- AgentBlueprint Compiler：把企业蓝图编译成框架无关中间表示，再由LangGraph适配器构建运行图。

默认多Agent模式使用Supervisor：Supervisor面向用户并维护会话；专业子Agent作为受控工具被调用。明确分类且适合并行的任务可以编译为Router与并行节点；需要专业Agent持续直接对话的流程使用Handoff。

## RAG决策

Blueprint支持三种策略：

- `two_step`：固定检索后生成。
- `agentic`：Retriever作为工具，由Agent决定何时调用。
- `hybrid`：固定首轮检索与按需补充检索结合。

知识权限过滤在检索前执行；引用信息在Retriever结果中保留，不能依靠模型事后猜测来源。

## 安全边界

LangChain工具只是模型可见适配层，真实调用仍必须经过AgentBlueprint Tool Executor：

```text
Agent Tool Call
→ 参数Schema
→ 租户与角色权限
→ Policy Engine
→ Approval Interrupt
→ Connector
→ Audit Event
```

模型和Agent均无权绕过此链路。

## 后果

正面影响：可以复用LangChain生态，并利用LangGraph实现持久状态、多Agent和人工审批。

需要承担：必须控制上下文传递、图状态版本和框架升级；Blueprint领域模型不能直接依赖LangChain类，否则规范会被具体框架接口绑死。
