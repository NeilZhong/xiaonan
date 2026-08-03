"""★ 案件推进智能体 API 路由 (POLICE_REQUIREMENTS §6.7)

提供：
  - 待确认任务草案列表
  - 主办民警确认 / 驳回任务草案
  - 侦查方向变更（重新规划）
  - 推进决策日志（可解释性展示）
  - 推进智能体开关
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user
from yuxi.services.police_advancement_service import police_advancement_service
from yuxi.storage.postgres.models_business import User

advancement_router = APIRouter(prefix="/police/advancement", tags=["police-advancement"])


class DraftConfirm(BaseModel):
    edits: dict | None = None  # 主办民警可修改的字段：title/description/priority/type/instructions/due_date


class DraftReject(BaseModel):
    reason: str | None = None


class DirectionChange(BaseModel):
    direction: str  # 新侦查方向


class AdvancementToggle(BaseModel):
    enabled: bool


@advancement_router.get("/{case_id}/drafts")
async def list_drafts(
    case_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """列出某案件的待确认任务草案（推进智能体生成，等主办民警审查）"""
    drafts = await police_advancement_service.list_drafts(case_id)
    return {"code": 0, "message": "success", "data": drafts}


@advancement_router.post("/tasks/{task_id}/confirm")
async def confirm_draft(
    task_id: int,
    body: DraftConfirm,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """主办民警确认任务草案 → 进入待分配状态"""
    result = await police_advancement_service.confirm_draft(task_id, current_user.id, body.edits)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 0, "message": "success", "data": result}


@advancement_router.post("/tasks/{task_id}/reject")
async def reject_draft(
    task_id: int,
    body: DraftReject,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """主办民警驳回任务草案 → 取消"""
    result = await police_advancement_service.reject_draft(task_id, current_user.id, body.reason)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 0, "message": "success", "data": result}


@advancement_router.post("/{case_id}/direction")
async def change_direction(
    case_id: int,
    body: DirectionChange,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """侦查方向变更：保留已完成任务，受影响任务标注，基于新方向重新规划"""
    if not body.direction or not body.direction.strip():
        raise HTTPException(status_code=422, detail="direction 不能为空")
    result = await police_advancement_service.change_direction(case_id, body.direction.strip(), current_user.id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "案件不存在"))
    return {"code": 0, "message": "success", "data": result}


@advancement_router.get("/{case_id}/logs")
async def list_logs(
    case_id: int,
    limit: int = 50,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """推进决策日志（可解释性展示）"""
    logs = await police_advancement_service.list_logs(case_id, limit=min(limit, 200))
    return {"code": 0, "message": "success", "data": logs}


@advancement_router.post("/{case_id}/toggle")
async def toggle(
    case_id: int,
    body: AdvancementToggle,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """启用 / 停用案件推进智能体（关闭即纯手动模式）"""
    result = await police_advancement_service.toggle(case_id, body.enabled, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="案件不存在")
    return {"code": 0, "message": "success", "data": result}
