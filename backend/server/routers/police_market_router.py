"""★ 小南市场 API 路由（模块 A）

探索浏览 / 申请使用 / 发布 / 超管审批：
- GET  /police/market/explore?type=&keyword=&category=&page=&page_size=
- GET  /police/market/{type}/{asset_id}        资产详情
- POST /police/market/{type}/{asset_id}/apply   申请使用（connect / equip_guided / install）
- POST /police/market/publish                   发布到市场（完整复刻，MVP）
- GET  /police/market/pending                   超管：待审列表
- POST /police/market/{request_type}/{request_id}/approve   超管审批
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from server.utils.auth_middleware import get_required_user, get_superadmin_user
from yuxi.services.police_market_service import police_market_service
from yuxi.storage.postgres.models_business import User


market_router = APIRouter(prefix="/police/market")


class PublishBody(BaseModel):
    type: str  # agent / partner / template
    asset_id: int
    reason: Optional[str] = None


class ApproveBody(BaseModel):
    approved: bool = False


# ── 探索浏览 ──────────────────────────────────────────

@market_router.get("/explore")
async def explore(
    type: str = Query("all", pattern="^(all|agent|partner|template)$"),
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_required_user),
):
    """市场探索列表（统一结构，前端一张卡片组件渲染）。"""
    try:
        return await police_market_service.explore(
            type=type, keyword=keyword, category=category,
            page=page, page_size=page_size, current_user=current_user,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@market_router.get("/{type}/{asset_id}")
async def detail(
    type: str,
    asset_id: int,
    current_user: User = Depends(get_required_user),
):
    """资产详情（按类型路由）。"""
    try:
        return await police_market_service.detail(
            type=type, asset_id=asset_id, current_user=current_user,
        )
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


# ── 申请使用 ──────────────────────────────────────────

@market_router.post("/{type}/{asset_id}/apply")
async def apply_asset(
    type: str,
    asset_id: int,
    current_user: User = Depends(get_required_user),
):
    """申请使用：agent→connect / partner→equip_guided / template→install。"""
    try:
        return await police_market_service.apply(
            type=type, asset_id=asset_id, current_user=current_user,
        )
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


# ── 发布与审核 ──────────────────────────────────────────

@market_router.post("/publish")
async def publish(
    body: PublishBody,
    current_user: User = Depends(get_required_user),
):
    """发布资产到市场（MVP 仅完整复刻）。权限：创建者或超管。"""
    try:
        return await police_market_service.publish(
            type=body.type, asset_id=body.asset_id, reason=body.reason,
            current_user=current_user,
        )
    except PermissionError as e:
        return JSONResponse(status_code=403, content={"error": str(e)})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@market_router.get("/pending")
async def pending(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_superadmin_user),
):
    """超管：市场待审列表（数字警员 + 协助伙伴全局共享申请）。"""
    return await police_market_service.pending(page=page, page_size=page_size)


@market_router.post("/{request_type}/{request_id}/approve")
async def approve(
    request_type: str,
    request_id: int,
    body: ApproveBody,
    current_user: User = Depends(get_superadmin_user),
):
    """超管：审批市场申请（agent / partner）。"""
    try:
        return await police_market_service.approve(
            request_type=request_type, request_id=request_id,
            approved=body.approved, reviewer_id=current_user.id,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
