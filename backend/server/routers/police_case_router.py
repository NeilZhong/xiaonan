"""★ 公安案件管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user
from yuxi.services.police_service import police_case_service
from yuxi.storage.postgres.models_business import User

case_router = APIRouter(prefix="/police/cases", tags=["police-cases"])


# ── 请求 Schema ──────────────────────────────────────────────

class CaseCreate(BaseModel):
    case_number: str = Field(..., max_length=50, description="案件编号")
    title: str = Field(..., max_length=200)
    case_type: str | None = None
    description: str | None = None
    phase: str = "research"
    priority: str = "medium"
    incident_date: str | None = None
    incident_location: str | None = None
    total_amount: float | None = None
    victim_info: dict | None = None
    suspect_info: list | None = None
    extra: dict | None = None


class CaseUpdate(BaseModel):
    title: str | None = None
    case_type: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    incident_date: str | None = None
    incident_location: str | None = None
    total_amount: float | None = None
    victim_info: dict | None = None
    suspect_info: list | None = None
    extra: dict | None = None


class MemberAdd(BaseModel):
    user_id: int
    role: str = "handler"  # commander/handler/reviewer/observer


class PhaseUpdate(BaseModel):
    phase: str  # research/arrest/handling/prosecution


# ── 路由 ──────────────────────────────────────────────────────

@case_router.get("")
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    phase: str | None = None,
    case_type: str | None = None,
    keyword: str | None = None,
    mine: bool = False,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """案件列表 (支持筛选/搜索/分页)"""
    user_id = current_user.id if mine else None
    result = await police_case_service.list_cases(
        skip=(page - 1) * page_size,
        limit=page_size,
        status=status,
        phase=phase,
        case_type=case_type,
        keyword=keyword,
        user_id=user_id,
    )
    return {"code": 0, "message": "success", "data": result}


@case_router.post("")
async def create_case(
    body: CaseCreate,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """创建案件"""
    data = body.model_dump(exclude_none=True)
    result = await police_case_service.create_case(data, current_user.id)
    return {"code": 0, "message": "success", "data": result}


@case_router.get("/{case_id}")
async def get_case(
    case_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """案件详情"""
    result = await police_case_service.get_case_detail(case_id)
    if not result:
        raise HTTPException(status_code=404, detail="案件不存在")
    return {"code": 0, "message": "success", "data": result}


@case_router.put("/{case_id}")
async def update_case(
    case_id: int,
    body: CaseUpdate,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """更新案件"""
    data = body.model_dump(exclude_none=True)
    result = await police_case_service.update_case(case_id, data, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="案件不存在")
    return {"code": 0, "message": "success", "data": result}


@case_router.delete("/{case_id}")
async def delete_case(
    case_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """删除案件"""
    ok = await police_case_service.delete_case(case_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="案件不存在")
    return {"code": 0, "message": "success"}


@case_router.post("/{case_id}/members")
async def add_member(
    case_id: int,
    body: MemberAdd,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """添加案件成员"""
    result = await police_case_service.add_member(case_id, body.user_id, body.role, current_user.id)
    return {"code": 0, "message": "success", "data": result}


@case_router.put("/{case_id}/phase")
async def update_phase(
    case_id: int,
    body: PhaseUpdate,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """切换案件阶段"""
    result = await police_case_service.update_phase(case_id, body.phase, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="案件不存在")
    return {"code": 0, "message": "success", "data": result}


@case_router.get("/{case_id}/timeline")
async def case_timeline(
    case_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """案件时间线"""
    result = await police_case_service.case_timeline(case_id)
    return {"code": 0, "message": "success", "data": result}
