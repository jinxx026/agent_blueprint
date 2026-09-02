"""Curated business module templates that enterprises can install and customize."""

from typing import TypedDict


class ModuleTemplate(TypedDict):
    key: str
    name: str
    category: str
    description: str
    agent_count: int
    risk_level: str
    knowledge_types: tuple[str, ...]
    connectors: tuple[str, ...]


MODULE_CATALOG: tuple[ModuleTemplate, ...] = (
    {
        "key": "customer-service",
        "name": "智能客服与售后",
        "category": "客户服务",
        "description": "回答政策问题、查询订单，并将退款等高风险动作交给人工审批。",
        "agent_count": 3,
        "risk_level": "medium",
        "knowledge_types": ("产品手册", "售后政策", "历史工单"),
        "connectors": ("CRM", "工单系统", "订单系统"),
    },
    {
        "key": "contract-review",
        "name": "合同审查助手",
        "category": "法务合规",
        "description": "识别风险条款、比对标准模板，并输出带原文引用的审查意见。",
        "agent_count": 4,
        "risk_level": "high",
        "knowledge_types": ("合同模板", "法务规则", "历史意见"),
        "connectors": ("合同系统", "文档库"),
    },
    {
        "key": "hr-policy",
        "name": "员工制度助手",
        "category": "人力资源",
        "description": "基于员工身份解释制度、福利和办事流程，隔离敏感人事数据。",
        "agent_count": 2,
        "risk_level": "medium",
        "knowledge_types": ("员工手册", "福利制度", "办事指南"),
        "connectors": ("HRIS", "企业门户"),
    },
    {
        "key": "sales-copilot",
        "name": "销售方案助手",
        "category": "销售增长",
        "description": "结合客户资料和产品能力生成拜访准备、方案草稿与跟进建议。",
        "agent_count": 3,
        "risk_level": "medium",
        "knowledge_types": ("产品资料", "客户画像", "成功案例"),
        "connectors": ("CRM", "邮件", "报价系统"),
    },
    {
        "key": "finance-audit",
        "name": "费用审核助手",
        "category": "财务运营",
        "description": "依据公司制度核验报销材料，标出异常并保留完整审计证据。",
        "agent_count": 3,
        "risk_level": "high",
        "knowledge_types": ("财务制度", "费用标准", "审计案例"),
        "connectors": ("ERP", "报销系统", "发票平台"),
    },
    {
        "key": "operations-sop",
        "name": "运营 SOP 助手",
        "category": "运营管理",
        "description": "将分散流程沉淀为可执行指引，遇到例外情况自动升级负责人。",
        "agent_count": 2,
        "risk_level": "low",
        "knowledge_types": ("SOP", "岗位手册", "异常案例"),
        "connectors": ("知识库", "任务系统"),
    },
)


def get_module_template(module_key: str) -> ModuleTemplate:
    for template in MODULE_CATALOG:
        if template["key"] == module_key:
            return template
    raise KeyError(module_key)
