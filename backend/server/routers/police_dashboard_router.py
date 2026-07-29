"""★ 公安工作台 API 路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user
from yuxi.services.police_service import police_dashboard_service
from yuxi.storage.postgres.models_business import User

dashboard_router = APIRouter(prefix="/police/dashboard", tags=["police-dashboard"])


@dashboard_router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """工作台统计数据"""
    result = await police_dashboard_service.get_stats(current_user.id)
    return {"code": 0, "message": "success", "data": result}


@dashboard_router.get("/my-tasks")
async def get_my_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """我的待办任务"""
    result = await police_dashboard_service.get_my_tasks(
        current_user.id, skip=(page - 1) * page_size, limit=page_size
    )
    return {"code": 0, "message": "success", "data": result}


@dashboard_router.get("/review-tasks")
async def get_review_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """待审核任务"""
    result = await police_dashboard_service.get_review_tasks(
        current_user.id, skip=(page - 1) * page_size, limit=page_size
    )
    return {"code": 0, "message": "success", "data": result}
