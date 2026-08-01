"""★ 数字警员 API 路由

融合 StaffDeck 数字员工概念：管理数字警员档案、能力、工作记录、SOP。
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

from yuxi.services.police_service import police_agent_service

agent_router = APIRouter(prefix="/police/agents")


# ── Pydantic Schemas ─────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    system_prompt: str
    model_settings: dict = Field(default={}, alias="model_config")
    badge_number: Optional[str] = None
    rank: Optional[str] = None
    specialty: Optional[str] = None
    avatar: Optional[str] = None
    department: Optional[str] = None
    color_theme: Optional[str] = None
    tools: list = []
    skills: list = []
    knowledge_base_ids: list = []
    capabilities: list = []
    sop_ids: list = []


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_settings: Optional[dict] = Field(default=None, alias="model_config")
    badge_number: Optional[str] = None
    rank: Optional[str] = None
    specialty: Optional[str] = None
    avatar: Optional[str] = None
    department: Optional[str] = None
    color_theme: Optional[str] = None
    tools: Optional[list] = None
    skills: Optional[list] = None
    knowledge_base_ids: Optional[list] = None
    capabilities: Optional[list] = None
    sop_ids: Optional[list] = None
    status: Optional[str] = None


class SOPCreate(BaseModel):
    name: str
    description: Optional[str] = None
    agent_type: Optional[str] = None
    category: Optional[str] = None
    states: list
    initial_state: str
    terminal_states: list = []
    input_schema: dict = {}
    output_template: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────

@agent_router.get("")
async def list_agents(
    type: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """数字警员列表"""
    return await police_agent_service.list_agents(
        type=type, status=status, keyword=keyword,
        page=page, page_size=page_size,
    )


@agent_router.get("/by-yuxi/{yuxi_agent_id}")
async def get_agent_by_yuxi(yuxi_agent_id: int):
    """按 yuxi 智能体主键 id 查询关联的数字警员档案（无关联返回 null）。

    统一智能体档案页路由携带 yuxi agent slug，前端先解析为 int 主键后再调用本接口，
    避免把 slug 字符串当作 police_agents 表的 int 主键传入导致 422。
    """
    return await police_agent_service.get_agent_by_yuxi(yuxi_agent_id)


@agent_router.get("/by-badge/{badge_number}")
async def get_agent_by_badge(badge_number: str):
    """按数字警员工号查询档案（档案页路由 /agent-manage/:badge_number 使用）。

    无记录返回 404。
    """
    result = await police_agent_service.get_agent_by_badge(badge_number)
    if not result:
        return JSONResponse(status_code=404, content={"error": "智能体不存在"})
    return result


# ── 市场模板端点 (须在 /{agent_id} 之前注册，避免被路径参数吞掉) ──

@agent_router.get("/templates")
async def list_templates(
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    source: Optional[str] = None,  # builtin / shared
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """智能体市场列表（内置模板 + 来自分享）"""
    return await police_agent_service.list_templates(
        category=category, keyword=keyword, page=page, page_size=page_size,
        source=source,
    )


@agent_router.post("/templates/{template_id}/install")
async def install_template(template_id: int):
    """一键安装模板：复制为新数字警员实例（自动生成工号 + 桥接 yuxi）

    失败返回 400，模板不存在返回 404。
    """
    result = await police_agent_service.install_template(template_id)
    if result is None:
        # 区分「模板不存在」和「安装过程失败」
        template = await police_agent_service.get_agent(template_id)
        if not template:
            return JSONResponse(status_code=404, content={"error": "模板不存在"})
        return JSONResponse(status_code=400, content={"error": "安装失败，请重试"})
    return result


# ── 共享与审批端点 ───────────────────────────────────────

@agent_router.post("/{agent_id}/share")
async def share_agent(agent_id: int, body: dict):
    """设置智能体共享范围（指定人 / 部门 / 全局）

    body: { scope: "personal"|"department"|"global", department_ids?, user_uids? }
    全局共享自动进入 pending 审批状态。
    """
    scope = body.get("scope", "personal")
    if scope not in ("personal", "department", "global"):
        return JSONResponse(status_code=400, content={"error": "无效的共享范围"})
    author_id = body.get("author_id")
    result = await police_agent_service.share_agent(
        agent_id,
        scope=scope,
        author_id=author_id,
        department_ids=body.get("department_ids"),
        user_uids=body.get("user_uids"),
    )
    if not result:
        return JSONResponse(status_code=404, content={"error": "智能体不存在"})
    return result


@agent_router.post("/{agent_id}/approve")
async def approve_agent(agent_id: int, body: dict):
    """管理员审批全局共享申请

    body: { approved: true|false, reviewer_id: int }
    """
    approved = body.get("approved", False)
    reviewer_id = body.get("reviewer_id")
    if reviewer_id is None:
        return JSONResponse(status_code=400, content={"error": "缺少审批人信息"})
    result = await police_agent_service.approve_agent(
        agent_id, approved=bool(approved), reviewer_id=reviewer_id,
    )
    if not result:
        agent = await police_agent_service.get_agent(agent_id)
        if not agent:
            return JSONResponse(status_code=404, content={"error": "智能体不存在"})
        return JSONResponse(status_code=400, content={"error": "该智能体无待审批的共享申请"})
    return result


# ── 单个数字警员 CRUD ─────────────────────────────────────

@agent_router.get("/{agent_id}")
async def get_agent(agent_id: int):
    """数字警员详情 (含最近运行记录 + 关联 SOP)"""
    agent = await police_agent_service.get_agent(agent_id)
    if not agent:
        return {"error": "Agent not found"}, 404
    return agent


@agent_router.post("")
async def create_agent(data: AgentCreate):
    """创建数字警员"""
    return await police_agent_service.create_agent(data.model_dump(by_alias=True))


@agent_router.put("/{agent_id}")
async def update_agent(agent_id: int, data: AgentUpdate):
    """更新数字警员"""
    result = await police_agent_service.update_agent(agent_id, data.model_dump(exclude_none=True, by_alias=True))
    if not result:
        return {"error": "Agent not found"}, 404
    return result


@agent_router.delete("/{agent_id}")
async def delete_agent(agent_id: int):
    """删除数字警员"""
    ok = await police_agent_service.delete_agent(agent_id)
    if not ok:
        return {"error": "Agent not found"}, 404
    return {"ok": True}


@agent_router.get("/{agent_id}/runs")
async def agent_runs(
    agent_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """数字警员运行记录"""
    return await police_agent_service.get_agent_runs(
        agent_id=agent_id, page=page, page_size=page_size,
    )


@agent_router.get("/sops/list")
async def list_sops(
    agent_type: Optional[str] = None,
    category: Optional[str] = None,
):
    """SOP 流程技能列表"""
    return await police_agent_service.list_sops(agent_type=agent_type, category=category)


@agent_router.get("/sops/{sop_id}")
async def get_sop(sop_id: int):
    """SOP 流程技能详情"""
    sop = await police_agent_service.get_sop(sop_id)
    if not sop:
        return {"error": "SOP not found"}, 404
    return sop


@agent_router.post("/sops")
async def create_sop(data: SOPCreate):
    """创建 SOP 流程技能"""
    return await police_agent_service.create_sop(data.model_dump())


@agent_router.put("/sops/{sop_id}")
async def update_sop(sop_id: int, data: SOPCreate):
    """更新 SOP 流程技能"""
    result = await police_agent_service.update_sop(sop_id, data.model_dump())
    if not result:
        return {"error": "SOP not found"}, 404
    return result


# ── 预设初始化 ───────────────────────────────────────────

@agent_router.post("/seed")
async def seed_preset_agents():
    """初始化预设数字警员 (幂等)"""
    return await police_agent_service.seed_preset_agents()
