"""★ 数字警员 API 路由

融合 StaffDeck 数字员工概念：管理数字警员档案、能力、工作记录、SOP。
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

from yuxi.services.police_service import police_agent_service
from yuxi.repositories.police_agent_repository import police_agent_repository
from yuxi.repositories.agent_repository import user_can_manage_agent
from server.utils.auth_middleware import get_required_user, get_superadmin_user
from yuxi.storage.postgres.models_business import User

agent_router = APIRouter(prefix="/police/agents")


# ── Pydantic Schemas ─────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # 业务类型（映射 Agent.agent_type）
    category: Optional[str] = None  # 功能分类（新建时下拉选择）
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
    status: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
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
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_required_user),
):
    """数字警员列表（按功能维度 category 筛选；后端按当前用户做可见性过滤）"""
    return await police_agent_service.list_agents(
        type=type, status=status, keyword=keyword, category=category,
        page=page, page_size=page_size, current_user=current_user,
    )


@agent_router.get("/pending")
async def list_pending_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_superadmin_user),
):
    """待审批（全局共享申请）列表，仅超级管理员可见。"""
    return await police_agent_service.list_pending_agents(
        page=page, page_size=page_size,
    )


@agent_router.get("/by-yuxi/{yuxi_agent_id}")
async def get_agent_by_yuxi(yuxi_agent_id: str):
    """按 yuxi 智能体主键 id 或 slug 查询数字警员档案（单表化后 agents.id 即 yuxi 主键）。

    支持数字主键或 slug（前端档案页统一以 agents.slug 作为智能体 id）。
    """
    agent = await police_agent_repository.resolve_by_identifier(yuxi_agent_id)
    if not agent:
        return None
    return await police_agent_service.get_agent_by_yuxi(agent.id)


@agent_router.get("/by-badge/{badge_number}")
async def get_agent_by_badge(badge_number: str):
    """按数字警员工号查询档案（档案页路由 /agent-manage/:badge_number 使用）。

    无记录返回 404。
    """
    result = await police_agent_service.get_agent_by_badge(badge_number)
    if not result:
        return JSONResponse(status_code=404, content={"error": "智能体不存在"})
    return result


# ── 共享与审批端点 ───────────────────────────────────────

@agent_router.post("/{agent_id}/share")
async def share_agent(
    agent_id: str,
    body: dict,
    current_user: User = Depends(get_required_user),
):
    """设置智能体共享范围（指定人 / 部门 / 全局）

    agent_id 支持数字主键、工号（大小写不敏感）或 yuxi 智能体 slug（前端统一用 slug）。
    body: { scope: "personal"|"department"|"user"|"global", department_ids?, user_uids? }
    - user:   「指定人」共享，写入 share_config.user_uids，直接生效无需审批
    - global: 全局共享自动进入 pending 审批状态
    """
    agent = await police_agent_repository.resolve_by_identifier(agent_id)
    if not agent:
        return JSONResponse(status_code=404, content={"error": "智能体不存在"})
    scope = body.get("scope", "personal")
    # 与 police_service.share_agent 保持一致：支持 personal / department / user / global 四种。
    # 前端 ShareConfigForm 的「指定人」发送 access_level='user'，此前白名单漏掉导致 400。
    if scope not in ("personal", "department", "user", "global"):
        return JSONResponse(status_code=400, content={"error": "无效的共享范围"})
    author_id = body.get("author_id") or current_user.id
    result = await police_agent_service.share_agent(
        agent.id,
        scope=scope,
        author_id=author_id,
        department_ids=body.get("department_ids"),
        user_uids=body.get("user_uids"),
    )
    if not result:
        return JSONResponse(status_code=404, content={"error": "智能体不存在"})
    return result


@agent_router.post("/{agent_id}/approve")
async def approve_agent(
    agent_id: str,
    body: dict,
    current_user: User = Depends(get_superadmin_user),
):
    """超级管理员审批全局共享申请

    agent_id 支持数字主键、工号（大小写不敏感）或 yuxi 智能体 slug。
    body: { approved: true|false }；审批人取自当前超级管理员身份。
    """
    agent = await police_agent_repository.resolve_by_identifier(agent_id)
    if not agent:
        return JSONResponse(status_code=404, content={"error": "智能体不存在"})
    approved = body.get("approved", False)
    result = await police_agent_service.approve_agent(
        agent.id, approved=bool(approved), reviewer_id=current_user.id,
    )
    if not result:
        return JSONResponse(status_code=400, content={"error": "该智能体无待审批的共享申请"})
    return result


# ── 单个数字警员 CRUD ─────────────────────────────────────

@agent_router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """数字警员详情 (含最近运行记录 + 关联 SOP)。agent_id 支持数字主键或 slug。"""
    agent = await police_agent_repository.resolve_by_identifier(agent_id)
    if not agent:
        return {"error": "Agent not found"}, 404
    result = await police_agent_service.get_agent(agent.id)
    if not result:
        return {"error": "Agent not found"}, 404
    return result


@agent_router.post("")
async def create_agent(
    data: AgentCreate,
    current_user: User = Depends(get_required_user),
):
    """创建数字警员（创建者记为当前用户，用于可见性过滤）"""
    payload = data.model_dump(by_alias=True)
    payload.setdefault("author_id", current_user.id)
    return await police_agent_service.create_agent(payload)


@agent_router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    current_user: User = Depends(get_required_user),
):
    """更新数字警员。agent_id 支持数字主键或 slug。

    权限（2026-08-06 收口）：仅创建者或超管可编辑，复用 yuxi user_can_manage_agent。
    """
    agent = await police_agent_repository.resolve_by_identifier(agent_id)
    if not agent:
        return {"error": "Agent not found"}, 404
    if not user_can_manage_agent(current_user, agent):
        return {"error": "无权编辑他人创建的数字警员"}, 403
    result = await police_agent_service.update_agent(agent.id, data.model_dump(exclude_none=True, by_alias=True))
    if not result:
        return {"error": "Agent not found"}, 404
    return result


@agent_router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_required_user),
):
    """删除数字警员。agent_id 支持数字主键或 slug。

    权限（2026-08-06 收口）：仅创建者或超管可删除；若该警员已参与案件运行则拒绝。
    """
    agent = await police_agent_repository.resolve_by_identifier(agent_id)
    if not agent:
        return {"error": "Agent not found"}, 404
    if not user_can_manage_agent(current_user, agent):
        return {"error": "无权删除他人创建的数字警员"}, 403
    # 检查是否已入案（存在绑定案件的运行记录则禁止删除，保护案件追溯）
    from sqlalchemy import select
    from yuxi.storage.postgres.manager import pg_manager
    from yuxi.storage.postgres.models_police import PoliceAgentRun
    async with pg_manager.get_async_session_context() as session:
        stmt = select(PoliceAgentRun.id).where(
            PoliceAgentRun.agent_id == agent.id,
            PoliceAgentRun.case_id.isnot(None),
        ).limit(1)
        bound = (await session.execute(stmt)).scalar_one_or_none()
    if bound:
        return {"error": "该数字警员已参与案件运行，禁止删除"}, 409
    ok = await police_agent_service.delete_agent(agent.id)
    if not ok:
        return {"error": "Agent not found"}, 404
    return {"ok": True}


@agent_router.get("/{agent_id}/runs")
async def agent_runs(
    agent_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """数字警员运行记录。agent_id 支持数字主键或 slug。"""
    agent = await police_agent_repository.resolve_by_identifier(agent_id)
    if not agent:
        return {"error": "Agent not found"}, 404
    return await police_agent_service.get_agent_runs(
        agent_id=agent.id, page=page, page_size=page_size,
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


# ── 留言板端点 ─────────────────────────────────────────

class CommentCreate(BaseModel):
    content: str
    rating: int | None = None


@agent_router.get("/{agent_id}/comments")
async def list_agent_comments(
    agent_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_required_user),
):
    """查询智能体留言列表。agent_id 支持数字主键或 slug。"""
    agent = await police_agent_repository.resolve_by_identifier(agent_id)
    if not agent:
        return JSONResponse(status_code=404, content={"error": "智能体不存在"})
    return await police_agent_service.list_comments(
        agent_id=agent.id, page=page, page_size=page_size,
    )


@agent_router.post("/{agent_id}/comments")
async def create_agent_comment(
    agent_id: str,
    data: CommentCreate,
    current_user: User = Depends(get_required_user),
):
    """创建留言。agent_id 支持数字主键或 slug。"""
    agent = await police_agent_repository.resolve_by_identifier(agent_id)
    if not agent:
        return JSONResponse(status_code=404, content={"error": "智能体不存在"})
    result = await police_agent_service.create_comment(
        agent_id=agent.id,
        content=data.content,
        user_id=current_user.id,
        rating=data.rating,
    )
    if not result:
        return JSONResponse(status_code=404, content={"error": "智能体不存在"})
    return result


@agent_router.delete("/{agent_id}/comments/{comment_id}")
async def delete_agent_comment(
    agent_id: str,
    comment_id: int,
    current_user: User = Depends(get_required_user),
):
    """删除留言（best-effort）。agent_id 支持数字主键或 slug。"""
    agent = await police_agent_repository.resolve_by_identifier(agent_id)
    if not agent:
        return JSONResponse(status_code=404, content={"error": "智能体不存在"})
    ok = await police_agent_service.delete_comment(
        agent_id=agent.id, comment_id=comment_id,
    )
    if not ok:
        return JSONResponse(status_code=404, content={"error": "留言不存在"})
    return {"ok": True}
