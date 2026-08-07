"""★ 站内通知 API 路由 — 任务截止提醒等面向民警的通知"""

from fastapi import APIRouter, Depends, Query

from server.utils.auth_middleware import get_required_user
from yuxi.services.police_due_reminder_service import police_due_reminder_service
from yuxi.storage.postgres.models_business import User

notification_router = APIRouter(prefix="/police/notifications", tags=["police-notifications"])


@notification_router.get("")
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_required_user),
):
    """查询当前用户的站内通知（未读优先，时间倒序）。"""
    items = await police_due_reminder_service.list_notifications(current_user.id, limit=limit)
    unread = await police_due_reminder_service.unread_count(current_user.id)
    return {"code": 0, "data": {"items": items, "unread": unread}}


@notification_router.get("/unread-count")
async def unread_count(current_user: User = Depends(get_required_user)):
    """未读通知数（工作台角标）。"""
    count = await police_due_reminder_service.unread_count(current_user.id)
    return {"code": 0, "data": {"unread": count}}


@notification_router.post("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_required_user),
):
    """标记单条通知已读。"""
    ok = await police_due_reminder_service.mark_read(current_user.id, notification_id)
    return {"code": 0 if ok else 404, "data": {"ok": ok}}
