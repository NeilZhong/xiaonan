"""★ 数字民警智能孵化 API 路由（模块 F）

- POST /police/incubation/create    从零孵化：生成草案（不落库，前端确认后走 create_agent）
- GET  /police/incubation/drafts     我创建的数字民警草稿（含完成度）
- POST /police/incubation/{agent_id}/refine  继续打磨：生成优化建议
- GET  /police/incubation/{agent_id}/completeness  单个民警完成度
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from server.utils.auth_middleware import get_required_user
from yuxi.services.police_incubation_service import police_incubation_service
from yuxi.storage.postgres.models_business import User


incubation_router = APIRouter(prefix="/police/incubation")


class CreateDraftBody(BaseModel):
    description: str
    target_users: Optional[str] = None
    responsibilities: Optional[str] = None
    usage_scenarios: Optional[str] = None
    model_hint: Optional[str] = None


class RefineBody(BaseModel):
    feedback: str
    focus: str = "all"  # soul / skills / connectors / all


@incubation_router.post("/create")
async def create_draft(
    body: CreateDraftBody,
    current_user: User = Depends(get_required_user),
):
    """从零孵化：根据描述规则化生成数字民警草案（确认后由前端创建）。"""
    try:
        return await police_incubation_service.create_draft(
            description=body.description, target_users=body.target_users,
            responsibilities=body.responsibilities, usage_scenarios=body.usage_scenarios,
            model_hint=body.model_hint, current_user=current_user,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@incubation_router.get("/drafts")
async def list_drafts(
    current_user: User = Depends(get_required_user),
):
    """我创建的数字民警草稿列表（含完成度进度条数据）。"""
    return await police_incubation_service.list_drafts(current_user)


@incubation_router.post("/{agent_id}/refine")
async def refine(
    agent_id: int,
    body: RefineBody,
    current_user: User = Depends(get_required_user),
):
    """继续打磨：基于反馈生成优化建议（确认后前端调 update_agent 应用）。"""
    try:
        return await police_incubation_service.refine(
            agent_id=agent_id, feedback=body.feedback, focus=body.focus,
            current_user=current_user,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@incubation_router.get("/{agent_id}/completeness")
async def completeness(
    agent_id: int,
    current_user: User = Depends(get_required_user),
):
    """单个数字民警完成度（灵魂/技能/连接器/审批）。"""
    result = await police_incubation_service.completeness(agent_id)
    if not result:
        return JSONResponse(status_code=404, content={"error": "数字民警不存在"})
    return result
