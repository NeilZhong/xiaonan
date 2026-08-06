"""★ 数字民警办案复盘 API 路由（模块 I.1）

- POST /police/reflections/trigger   任务后反思触发（模式A，规则化判定）
- POST /police/reflections           显式创建复盘记录（draft）
- GET  /police/reflections           记录列表（本人 + 超管可见全部）
- GET  /police/reflections/{id}      记录详情
- POST /police/reflections/{id}/review  民警审阅（approve/reject）
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from server.utils.auth_middleware import get_required_user
from yuxi.services.police_reflection_service import police_reflection_service
from yuxi.storage.postgres.models_business import User


reflection_router = APIRouter(prefix="/police/reflections")


class CreateReflectionBody(BaseModel):
    agent_id: Optional[int] = None
    case_id: Optional[int] = None
    trigger_type: str  # A / B
    phase: str  # memory / skill / profile / repair
    source: str = "conversation"
    payload: Optional[dict] = None


class TriggerBody(BaseModel):
    agent_id: Optional[int] = None
    case_id: Optional[int] = None
    conversation_summary: str


class ReviewBody(BaseModel):
    action: str  # approve / reject


@reflection_router.post("/trigger")
async def trigger_reflection(
    body: TriggerBody,
    current_user: User = Depends(get_required_user),
):
    """任务后反思触发（模式A）：对对话摘要做规则化判定，按需生成 1-3 条记录。"""
    return await police_reflection_service.trigger_reflection(
        agent_id=body.agent_id, case_id=body.case_id,
        conversation_summary=body.conversation_summary, current_user=current_user,
    )


@reflection_router.post("")
async def create_reflection(
    body: CreateReflectionBody,
    current_user: User = Depends(get_required_user),
):
    """显式创建复盘记录（draft，待审阅）。"""
    result = await police_reflection_service.create_record(
        agent_id=body.agent_id, case_id=body.case_id,
        trigger_type=body.trigger_type, phase=body.phase,
        source=body.source, payload=body.payload, current_user=current_user,
    )
    return result


@reflection_router.get("")
async def list_reflections(
    trigger_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_required_user),
):
    """复盘记录列表（本人 + 超管全部；支持 trigger_type/status 过滤）。"""
    return await police_reflection_service.list_records(
        current_user=current_user, trigger_type=trigger_type, status=status,
        page=page, page_size=page_size,
    )


@reflection_router.get("/{record_id}")
async def get_reflection(
    record_id: int,
    current_user: User = Depends(get_required_user),
):
    """复盘记录详情。"""
    result = await police_reflection_service.get_record(record_id)
    if not result:
        return JSONResponse(status_code=404, content={"error": "复盘记录不存在"})
    return result


@reflection_router.post("/{record_id}/review")
async def review_reflection(
    record_id: int,
    body: ReviewBody,
    current_user: User = Depends(get_required_user),
):
    """民警审阅：approve→applied（技能沉淀自动入模板库）/ reject→rejected。"""
    try:
        return await police_reflection_service.review_record(
            record_id=record_id, action=body.action, current_user=current_user,
        )
    except PermissionError as e:
        return JSONResponse(status_code=403, content={"error": str(e)})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
