# ADR-0004：Compiler先生成可移植ExecutionPlan

状态：Accepted  
日期：2026-08-31

## 背景

Blueprint需要最终运行在LangChain与LangGraph上，但企业业务契约不应直接保存Python对象、Prompt模板实例或某个框架版本的Graph对象。否则框架升级会迫使企业修改蓝图，也很难对编译结果做稳定回归测试。

## 决策

Compiler先生成可序列化、不可变、框架无关的 `ExecutionPlan`。它包含：

- 来源Blueprint版本和规范版本。
- Blueprint规范化内容的SHA-256哈希。
- 每个Agent的系统指令和最小资源绑定。
- 每个Agent的Retriever规格。
- 工具、权限风险和审批绑定。
- 已解析的确定性Policy条件。
- Graph节点、边、触发器和执行限制。
- 评测数据集与发布阈值。

下一阶段的LangGraph Adapter只负责把ExecutionPlan翻译为LangChain Agent、Retriever、Tool和StateGraph。

## 确定性

ExecutionPlan不包含编译时间、随机ID或环境地址。相同Blueprint必须得到相同Plan与Plan ID：

```text
plan_id = blueprint_name + version + compiler_version + content_hash前12位
```

部署时间、部署人和环境属于未来的Deployment对象，不属于编译结果。

## Policy安全

Compiler只支持受限比较表达式，例如：

```text
amount <= 5000
customer_identity_verified == true
```

表达式被解析为字段、运算符和值，禁止使用Python `eval`或任意脚本。

## 后果

正面影响：编译结果可缓存、比较、签名、评测和跨框架适配。

需要承担：需要维护ExecutionPlan版本迁移；LangGraph新增能力必须先映射到稳定IR，而不能从API路由直接调用框架对象。
