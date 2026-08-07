"""★ 案件任务统计 API 路由

端点挂在 /police/cases 资源下，路径为 /{case_id}/stats，
语义对齐需求规格的 GET /api/projects/{id}/stats（projects = 案件）。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user
from yuxi.services.police_stats_service import police_case_stats_service
from yuxi.storage.postgres.models_business import User

stats_router = APIRouter(prefix="/police/cases", tags=["police-stats"])


@stats_router.get("/{case_id}/stats")
async def get_case_stats(
    case_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """案件任务统计：人机占比 / 燃尽 / 概览指标 / 风险汇总"""
    result = await police_case_stats_service.get_case_stats(case_id, db)
    return {"code": 0, "message": "success", "data": result}
