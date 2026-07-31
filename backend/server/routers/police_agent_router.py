"""★ 数字警员 API 路由

融合 StaffDeck 数字员工概念：管理数字警员档案、能力、工作记录、SOP。
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional

from yuxi.services.police_service import police_agent_service

agent_router = APIRouter(prefix="/police/agents")


# ── Pydantic Schemas ─────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    system_prompt: str
    model_config: dict
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
    model_config: Optional[dict] = None
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
    return await police_agent_service.create_agent(data.model_dump())


@agent_router.put("/{agent_id}")
async def update_agent(agent_id: int, data: AgentUpdate):
    """更新数字警员"""
    result = await police_agent_service.update_agent(agent_id, data.model_dump(exclude_none=True))
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


@agent_router.post("/seed")
async def seed_preset_agents():
    """初始化预设数字警员 (幂等)"""
    return await police_agent_service.seed_preset_agents()
