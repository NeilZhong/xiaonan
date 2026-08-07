import os

from fastapi import APIRouter

from server.routers.agent_invocation_router import agent_invocation_router
from server.routers.agent_router import agent_router
from server.routers.auth_dept_router import department
from server.routers.auth_router import auth
from server.routers.chat_router import chat
from server.routers.dashboard_router import dashboard
from server.routers.filesystem_router import filesystem_router
from server.routers.mcp_router import mcp
from server.routers.mention_router import mention_router
from server.routers.model_provider_router import model_providers
from server.routers.skill_router import skills, user_skills
from server.routers.system_router import system
from server.routers.system_task_router import tasks
from server.routers.tool_router import tools
from server.routers.user_router import user_router
from server.routers.workspace_router import workspace

# ★ 公安业务路由
from server.routers.police_case_router import case_router as police_case_router
from server.routers.police_task_router import task_router as police_task_router
from server.routers.police_evidence_router import evidence_router as police_evidence_router
from server.routers.police_dashboard_router import dashboard_router as police_dashboard_router
from server.routers.police_stats_router import stats_router as police_stats_router
from server.routers.police_agent_router import agent_router as police_agent_router
from server.routers.police_workspace_router import workspace_router as police_workspace_router
from server.routers.police_import_router import import_router as police_import_router
from server.routers.police_advancement_router import advancement_router as police_advancement_router
from server.routers.police_task_template_router import task_template_router as police_task_template_router
from server.routers.police_audit_router import audit_router as police_audit_router
from server.routers.police_partner_router import (
    partner_router as police_partner_router,
    equip_router as police_equip_router,
    connection_router as police_connection_router,
)
from server.routers.police_agent_version_router import version_router as police_version_router
from server.routers.police_governance_router import governance_router as police_governance_router
from server.routers.police_market_router import market_router as police_market_router
from server.routers.police_reflection_router import reflection_router as police_reflection_router
from server.routers.police_incubation_router import incubation_router as police_incubation_router
from server.routers.police_notification_router import notification_router as police_notification_router

_LITE_MODE = os.environ.get("LITE_MODE", "").lower() in ("true", "1")

router = APIRouter()

# 基础系统接口：健康检查、配置、认证与聊天主链路。
router.include_router(system)  # /api/system/* 系统状态与全局配置
router.include_router(auth)  # /api/auth/* 登录、用户信息与 CLI 浏览器登录授权
router.include_router(agent_router)  # /api/agent/* 智能体管理与运行态
router.include_router(agent_invocation_router)  # /api/agent-invocation/* 外部 Agent 调用与评估
router.include_router(chat)  # /api/chat/* 对话线程、消息历史与附件

# 管理与工作台接口：后台任务、权限域以及工具体系配置。
router.include_router(dashboard)  # /api/dashboard/* 仪表盘聚合数据
router.include_router(department)  # /api/departments/* 部门与权限相关数据
router.include_router(tasks)  # /api/tasks/* 后台任务查询与管理
router.include_router(mcp)  # /api/system/mcp-servers/* MCP 服务管理
router.include_router(model_providers)  # /api/system/model-providers/* 独立模型配置
router.include_router(skills)  # /api/system/skills/* Skills 管理
router.include_router(user_skills)  # /api/skills/* 用户可用 Skills
router.include_router(tools)  # /api/system/tools/* 工具列表与配置
router.include_router(user_router)  # /api/user/* 用户级配置与凭据
router.include_router(filesystem_router)  # /api/viewer/filesystem/* 工作台文件系统视图
router.include_router(workspace)  # /api/workspace/* 用户个人工作区
router.include_router(mention_router)  # /api/mention/* 提及文件搜索接口

# ★ 公安业务接口：案件、任务、证据、工作台
router.include_router(police_case_router)       # /api/police/cases/*
router.include_router(police_stats_router)      # /api/police/cases/*/stats
router.include_router(police_task_router)       # /api/police/tasks/*
router.include_router(police_evidence_router)   # /api/police/evidence/*
router.include_router(police_dashboard_router)  # /api/police/dashboard/*
router.include_router(police_agent_router)      # /api/police/agents/* 数字警员 + SOP
router.include_router(police_workspace_router)   # /api/police/workspaces/* 案件独立工作区
router.include_router(police_import_router)       # /api/police/import/* 笔录导入与智能建案
router.include_router(police_advancement_router)   # /api/police/advancement/* 案件推进智能体
router.include_router(police_task_template_router)  # /api/police/task-templates/* 侦查任务模板配置
router.include_router(police_market_router)          # /api/police/market/* 市场探索/发布/审核
router.include_router(police_reflection_router)      # /api/police/reflections/* 办案复盘（任务后反思+技能自修复）
router.include_router(police_incubation_router)      # /api/police/incubation/* 智能孵化（从零孵化/继续打磨）
router.include_router(police_audit_router)           # /api/police/audit/* 审计统计/查询/校验 (§10.7)
router.include_router(police_partner_router)         # /api/police/partners/* 协助伙伴（子智能体）CRUD
router.include_router(police_equip_router)           # /api/police/agents/:id/partners/* 数字警员装备区
router.include_router(police_connection_router)      # /api/police/agent-connections/* 用户↔数字警员连接
router.include_router(police_version_router)         # /api/police/agents/:id/(versions|switch-mode|health) 版本与发布控制
router.include_router(police_governance_router)      # /api/police/admin/* 治理后台：审核台与运行中心
router.include_router(police_notification_router)    # /api/police/notifications/* 站内通知（截止提醒）

if not _LITE_MODE:
    from server.routers.external_kb_router import external_kb
    from server.routers.graph_router import graph
    from server.routers.knowledge_eval_router import evaluation
    from server.routers.knowledge_router import knowledge

    # 知识库与图谱能力依赖较重，LITE 模式下跳过这组接口。
    router.include_router(external_kb)  # /api/knowledge/databases/external* CLI 与外部 Agent 调用
    router.include_router(knowledge)  # /api/knowledge/* 知识库管理与检索
    router.include_router(evaluation)  # /api/evaluation/* 知识库评估
    router.include_router(graph)  # /api/graph/* 图谱查询与管理
