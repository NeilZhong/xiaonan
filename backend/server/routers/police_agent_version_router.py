"""★ 数字警员版本与发布控制 API 路由（运行中心）

- GET    /police/agents/:id/versions          版本历史
- POST   /police/agents/:id/switch-mode        切换流动/受控发布
- POST   /police/agents/:id/versions/:vid/publish  手动发布草稿
- POST   /police/agents/:id/versions/:vid/rollback  回滚到指定版本
- GET    /police/agents/:id/health             资产健康度

权限：switch-mode / publish / rollback 仅超管或警员作者（user_can_manage_agent）。
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from yuxi.services.police_agent_version_service import police_agent_version_service
from yuxi.repositories.agent_repository import user_can_manage_agent
from yuxi.repositories.police_agent_repository import police_agent_repository
from server.utils.auth_middleware import get_required_user
from yuxi.storage.postgres.models_business import User

version_router = APIRouter(prefix="/police/agents")


class SwitchModeBody(BaseModel):
    mode: str  # rolling / controlled


@version_router.get("/{agent_id}/versions")
async def list_versions(
    agent_id: int,
    include_snapshot: bool = Query(False),
):
    """版本历史（最新在前）。"""
    try:
        return await police_agent_version_service.list_versions(
            agent_id=agent_id, include_snapshot=include_snapshot,
        )
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


@version_router.post("/{agent_id}/switch-mode")
async def switch_mode(
    agent_id: int,
    body: SwitchModeBody,
    current_user: User = Depends(get_required_user),
):
    """切换发布模式（流动版本/受控发布）。超管或作者可用。"""
    agent = await police_agent_repository.get_by_id(agent_id)
    if not agent:
        return JSONResponse(status_code=404, content={"error": "数字警员不存在"})
    if not user_can_manage_agent(current_user, agent):
        return JSONResponse(status_code=403, content={"error": "无权修改他人创建的数字警员"})
    try:
        return await police_agent_version_service.switch_mode(
            agent_id=agent_id, mode=body.mode, current_user=current_user,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@version_router.post("/{agent_id}/versions/{version_id}/publish")
async def publish_draft(
    agent_id: int,
    version_id: int,
    current_user: User = Depends(get_required_user),
):
    """手动发布草稿版本（受控发布模式）。超管或作者可用。"""
    agent = await police_agent_repository.get_by_id(agent_id)
    if not agent:
        return JSONResponse(status_code=404, content={"error": "数字警员不存在"})
    if not user_can_manage_agent(current_user, agent):
        return JSONResponse(status_code=403, content={"error": "无权修改他人创建的数字警员"})
    try:
        return await police_agent_version_service.publish_draft(
            agent_id=agent_id, current_user=current_user,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@version_router.post("/{agent_id}/versions/{version_id}/rollback")
async def rollback(
    agent_id: int,
    version_id: int,
    current_user: User = Depends(get_required_user),
):
    """回滚到指定历史版本。超管或作者可用。"""
    agent = await police_agent_repository.get_by_id(agent_id)
    if not agent:
        return JSONResponse(status_code=404, content={"error": "数字警员不存在"})
    if not user_can_manage_agent(current_user, agent):
        return JSONResponse(status_code=403, content={"error": "无权修改他人创建的数字警员"})
    try:
        return await police_agent_version_service.rollback(
            agent_id=agent_id, version_id=version_id, current_user=current_user,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@version_router.get("/{agent_id}/health")
async def agent_health(agent_id: int):
    """资产健康度（版本同步状态）。"""
    try:
        return await police_agent_version_service.health(agent_id=agent_id)
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})
