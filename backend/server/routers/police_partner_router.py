"""★ 协助伙伴（子智能体）API 路由

覆盖：
1. 协助伙伴 CRUD（/police/partners）—— 编辑/删除仅创建者或超管。
2. 数字警员装备区（/police/agents/:id/partners）—— 装备/卸载/候选。
3. 用户 ↔ 数字警员连接（/police/agent-connections）—— 市场「申请使用」。

委派运行时（task/subagent_start）由 Yuxi 中间件处理，本路由只做数据层与权限层。
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from yuxi.services.police_partner_service import police_partner_service
from yuxi.repositories.police_agent_repository import police_agent_repository
from yuxi.services.police_binding_service import agent_binding_service
from server.utils.auth_middleware import get_required_user, get_superadmin_user
from yuxi.storage.postgres.models_business import User


# ── 三个路由（前缀拆分，避免与 police_agent_router 冲突） ──
partner_router = APIRouter(prefix="/police/partners")
equip_router = APIRouter(prefix="/police/agents")
connection_router = APIRouter(prefix="/police/agent-connections")


# ── Pydantic Schemas ─────────────────────────────────────────

class PartnerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    system_prompt: Optional[str] = None
    model_settings: Optional[dict] = None
    tools: Optional[list] = None
    skills: Optional[list] = None
    knowledge_base_ids: Optional[list] = None
    sop_ids: Optional[list] = None


class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    system_prompt: Optional[str] = None
    model_settings: Optional[dict] = None
    tools: Optional[list] = None
    skills: Optional[list] = None
    knowledge_base_ids: Optional[list] = None
    sop_ids: Optional[list] = None


class ShareBody(BaseModel):
    scope: str
    department_ids: Optional[list] = None
    user_uids: Optional[list] = None


class ApproveBody(BaseModel):
    approved: bool = False


class ApplyConnectionBody(BaseModel):
    agent_id: int


class PinBody(BaseModel):
    version_id: int


class PrefsBody(BaseModel):
    nickname: Optional[str] = None
    notify_new_version: Optional[bool] = None


class AssociatePartnersBody(BaseModel):
    partner_ids: list[int]


# ── 协助伙伴 CRUD ──────────────────────────────────────────

@partner_router.get("")
async def list_partners(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_required_user),
):
    """协助伙伴列表（仅返回 is_subagent=true；可见性复用共享体系）。"""
    return await police_partner_service.list_partners(
        current_user=current_user, keyword=keyword, category=category,
        status=status, page=page, page_size=page_size,
    )


@partner_router.get("/{partner_id}")
async def get_partner(partner_id: int):
    """协助伙伴详情。"""
    result = await police_partner_service.get_partner(partner_id)
    if not result:
        return JSONResponse(status_code=404, content={"error": "协助伙伴不存在"})
    return result


@partner_router.post("")
async def create_partner(
    data: PartnerCreate,
    current_user: User = Depends(get_required_user),
):
    """创建协助伙伴（强制 is_subagent=true + SubAgentBackend）。"""
    result = await police_partner_service.create_partner(
        data=data.model_dump(exclude_none=True), current_user=current_user,
    )
    return result


@partner_router.put("/{partner_id}")
async def update_partner(
    partner_id: int,
    data: PartnerUpdate,
    current_user: User = Depends(get_required_user),
):
    """编辑协助伙伴。权限：仅创建者或超管。"""
    try:
        result = await police_partner_service.update_partner(
            partner_id=partner_id, data=data.model_dump(exclude_none=True),
            current_user=current_user,
        )
    except PermissionError as e:
        return JSONResponse(status_code=403, content={"error": str(e)})
    if not result:
        return JSONResponse(status_code=404, content={"error": "协助伙伴不存在"})
    return result


@partner_router.delete("/{partner_id}")
async def delete_partner(
    partner_id: int,
    current_user: User = Depends(get_required_user),
):
    """删除协助伙伴。权限：仅创建者或超管；被挂载时返回 409。"""
    try:
        ok = await police_partner_service.delete_partner(
            partner_id=partner_id, current_user=current_user,
        )
    except PermissionError as e:
        return JSONResponse(status_code=403, content={"error": str(e)})
    except ValueError as e:
        return JSONResponse(status_code=409, content={"error": str(e)})
    if not ok:
        return JSONResponse(status_code=404, content={"error": "协助伙伴不存在"})
    return {"ok": True}


@partner_router.post("/{partner_id}/share")
async def share_partner(
    partner_id: int,
    body: ShareBody,
    current_user: User = Depends(get_required_user),
):
    """设置协助伙伴共享范围（与数字警员 share 同语义，不授警号）。"""
    try:
        result = await police_partner_service.share_partner(
            partner_id=partner_id, scope=body.scope,
            author_id=current_user.id,
            department_ids=body.department_ids, user_uids=body.user_uids,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    if not result:
        return JSONResponse(status_code=404, content={"error": "协助伙伴不存在"})
    return result


@partner_router.post("/{partner_id}/approve")
async def approve_partner(
    partner_id: int,
    body: ApproveBody,
    current_user: User = Depends(get_superadmin_user),
):
    """超管审批协助伙伴全局共享申请（不授警号）。"""
    result = await police_partner_service.approve_partner(
        partner_id=partner_id, approved=body.approved, reviewer_id=current_user.id,
    )
    if not result:
        return JSONResponse(status_code=400, content={"error": "该协助伙伴无待审批的共享申请"})
    return result


# ── 数字警员装备区 ─────────────────────────────────────────

@equip_router.get("/{agent_id}/partners")
async def list_equipped_partners(agent_id: int):
    """数字警员已装备的协助伙伴（空间资产）。"""
    result = await police_partner_service.list_equipped(agent_id=agent_id)
    return result


@equip_router.get("/{agent_id}/partners/available")
async def list_available_partners(
    agent_id: int,
    current_user: User = Depends(get_required_user),
):
    """当前用户空间可装备但未装备的协助伙伴候选（天赋资产）。"""
    return await police_partner_service.list_available(
        agent_id=agent_id, current_user=current_user,
    )


@equip_router.post("/{agent_id}/partners/{partner_id}/equip")
async def equip_partner(
    agent_id: int,
    partner_id: int,
    current_user: User = Depends(get_required_user),
):
    """给数字警员装备协助伙伴。权限：仅该警员的创建者或超管。"""
    try:
        result = await police_partner_service.equip_partner(
            agent_id=agent_id, partner_id=partner_id, current_user=current_user,
        )
    except PermissionError as e:
        return JSONResponse(status_code=403, content={"error": str(e)})
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})
    return result


@equip_router.post("/{agent_id}/partners/{partner_id}/unequip")
async def unequip_partner(
    agent_id: int,
    partner_id: int,
    current_user: User = Depends(get_required_user),
):
    """从数字警员卸载协助伙伴。权限：仅该警员的创建者或超管。"""
    try:
        result = await police_partner_service.unequip_partner(
            agent_id=agent_id, partner_id=partner_id, current_user=current_user,
        )
    except PermissionError as e:
        return JSONResponse(status_code=403, content={"error": str(e)})
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})
    return result


# ── 用户 ↔ 数字警员连接 ───────────────────────────────────

@connection_router.get("")
async def list_connections(
    status: Optional[str] = None,
    current_user: User = Depends(get_required_user),
):
    """当前用户的数字警员连接列表（我的数字警员）。"""
    return await police_partner_service.list_connections(
        current_user=current_user, status=status,
    )


@connection_router.get("/mine")
async def list_my_bindings(current_user: User = Depends(get_required_user)):
    """当前用户全部绑定（含源智能体摘要、钉住的版本、关联伙伴）。P2c 富视图。"""
    return await agent_binding_service.list_mine(current_user=current_user)


@connection_router.post("")
async def apply_connection(
    body: ApplyConnectionBody,
    current_user: User = Depends(get_required_user),
):
    """申请连接数字警员（市场「申请使用」；建立连接不复制警员，并级联添加其关联伙伴）。"""
    try:
        result = await agent_binding_service.apply(
            agent_id=body.agent_id, current_user=current_user,
        )
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})
    return result


@connection_router.post("/{connection_id}/pin")
async def pin_version(
    connection_id: int,
    body: PinBody,
    current_user: User = Depends(get_required_user),
):
    """钉住某版本（version_id 须属于该智能体）。"""
    try:
        return await agent_binding_service.pin(
            connection_id=connection_id, version_id=body.version_id, current_user=current_user,
        )
    except (ValueError, PermissionError) as e:
        code = 400 if isinstance(e, ValueError) else 403
        return JSONResponse(status_code=code, content={"error": str(e)})


@connection_router.delete("/{connection_id}/pin")
async def unpin_version(
    connection_id: int,
    current_user: User = Depends(get_required_user),
):
    """取消钉版本（恢复跟随源智能体当前版本）。"""
    try:
        return await agent_binding_service.unpin(
            connection_id=connection_id, current_user=current_user,
        )
    except (ValueError, PermissionError) as e:
        code = 400 if isinstance(e, ValueError) else 403
        return JSONResponse(status_code=code, content={"error": str(e)})


@connection_router.patch("/{connection_id}")
async def update_prefs(
    connection_id: int,
    body: PrefsBody,
    current_user: User = Depends(get_required_user),
):
    """修改绑定偏好：昵称 / 新版通知。不影响源智能体定义。"""
    try:
        return await agent_binding_service.set_prefs(
            connection_id=connection_id, current_user=current_user,
            nickname=body.nickname, notify_new_version=body.notify_new_version,
        )
    except (ValueError, PermissionError) as e:
        code = 400 if isinstance(e, ValueError) else 403
        return JSONResponse(status_code=code, content={"error": str(e)})


@connection_router.delete("/{connection_id}")
async def delete_connection(
    connection_id: int,
    current_user: User = Depends(get_required_user),
):
    """解除绑定（仅本人或超管；级联添加的伙伴连接独立生命周期，保留不删）。"""
    try:
        await agent_binding_service.remove(
            connection_id=connection_id, current_user=current_user,
        )
    except (ValueError, PermissionError) as e:
        code = 404 if isinstance(e, ValueError) else 403
        return JSONResponse(status_code=code, content={"error": str(e)})
    return {"ok": True}


# ── 数字警察 ↔ 协助伙伴 关联（创建者侧，P2c）─────────────────

@equip_router.get("/{agent_id}/associate-partners")
async def list_associate_partners(
    agent_id: int,
    current_user: User = Depends(get_required_user),
):
    """列出某数字警员关联的协助伙伴（创建者/超管可见）。"""
    try:
        return await agent_binding_service.list_partners(
            agent_id=agent_id, current_user=current_user,
        )
    except (ValueError, PermissionError) as e:
        code = 404 if isinstance(e, ValueError) else 403
        return JSONResponse(status_code=code, content={"error": str(e)})


@equip_router.put("/{agent_id}/associate-partners")
async def set_associate_partners(
    agent_id: int,
    body: AssociatePartnersBody,
    current_user: User = Depends(get_required_user),
):
    """设置某数字警员的关联协助伙伴（全量替换；仅创建者/超管）。用于添加时级联。"""
    try:
        return await agent_binding_service.set_partners(
            agent_id=agent_id, partner_ids=body.partner_ids, current_user=current_user,
        )
    except (ValueError, PermissionError) as e:
        code = 404 if isinstance(e, ValueError) else 403
        return JSONResponse(status_code=code, content={"error": str(e)})
