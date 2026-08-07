"""★ 小南治理后台 API 路由（P3）——审核台 + 运行中心

审核台（超管）：
- GET  /police/admin/review/pending                        待审列表（新建待审 + 全局共享申请）
- GET  /police/admin/review/{agent_id}                     待审详情（全量配置 + 关联伙伴 + 版本基线）
- POST /police/admin/review/{agent_id}/preview             以草稿配置试跑单轮对话（不落运行记录）
- POST /police/admin/review/{request_type}/{request_id}/decide   通过 / 驳回（含理由）

运行中心（超管）：
- GET  /police/admin/runtime-config                        平台默认运行模式
- PUT  /police/admin/runtime-config                        设置平台默认运行模式
- GET  /police/admin/runtime-overview                      状态总览（在线/模式/草稿/绑定数）

逐个智能体的 rolling/controlled 切换复用既有 POST /police/agents/{id}/switch-mode。
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from server.utils.auth_middleware import get_superadmin_user
from yuxi.services.police_governance_service import police_governance_service
from yuxi.storage.postgres.models_business import User


governance_router = APIRouter(prefix="/police/admin")


class DecideBody(BaseModel):
    approved: bool = False
    reason: str | None = None


class PreviewBody(BaseModel):
    message: str
    use_draft: bool = True


class RuntimeConfigBody(BaseModel):
    default_release_mode: str


# ── 审核台 ──────────────────────────────────────────

@governance_router.get("/review/pending")
async def review_pending(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_superadmin_user),
):
    """待审列表：数字警员与协助伙伴统一结构。"""
    return await police_governance_service.review_pending(page=page, page_size=page_size)


@governance_router.get("/review/{agent_id}")
async def review_detail(
    agent_id: int,
    current_user: User = Depends(get_superadmin_user),
):
    """待审详情：全量配置 + 关联伙伴 + 版本基线。"""
    try:
        return await police_governance_service.review_detail(agent_id=agent_id)
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


@governance_router.post("/review/{agent_id}/preview")
async def review_preview(
    agent_id: int,
    body: PreviewBody,
    current_user: User = Depends(get_superadmin_user),
):
    """预览对话试跑：优先加载草稿配置，不写任何正式运行记录。"""
    try:
        return await police_governance_service.preview_run(
            agent_id=agent_id, message=body.message, use_draft=body.use_draft,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        # 试跑失败不得阻断审核动作，返回可读错误供前端提示
        return JSONResponse(status_code=502, content={"error": f"试跑失败: {e}"})


@governance_router.post("/review/{request_type}/{request_id}/decide")
async def review_decide(
    request_type: str,
    request_id: int,
    body: DecideBody,
    current_user: User = Depends(get_superadmin_user),
):
    """审核通过 / 驳回（幂等：非待审项返回 400）。"""
    try:
        return await police_governance_service.review_decide(
            request_type=request_type, request_id=request_id,
            approved=body.approved, reason=body.reason, current_user=current_user,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


# ── 运行中心 ──────────────────────────────────────────

@governance_router.get("/runtime-config")
async def get_runtime_config(
    current_user: User = Depends(get_superadmin_user),
):
    """平台默认运行模式（默认 controlled 受控发布）。"""
    return await police_governance_service.get_runtime_config()


@governance_router.put("/runtime-config")
async def set_runtime_config(
    body: RuntimeConfigBody,
    current_user: User = Depends(get_superadmin_user),
):
    """设置平台默认运行模式，仅影响此后新建智能体的初始发布状态。"""
    try:
        return await police_governance_service.set_runtime_config(
            default_release_mode=body.default_release_mode, current_user=current_user,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@governance_router.get("/runtime-overview")
async def runtime_overview(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_superadmin_user),
):
    """状态总览：在线状态 / 当前运行模式 / 待发布草稿 / 绑定规模。"""
    return await police_governance_service.runtime_overview(page=page, page_size=page_size)
