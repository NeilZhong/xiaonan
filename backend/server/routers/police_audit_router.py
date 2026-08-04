"""★ 审计 API 路由 (POLICE_REQUIREMENTS §10.7)

提供审计统计、审计日志查询、案件维度审计视图与哈希链校验接口。
可见性：全局审计为系统管理员独占；案件维度审计对案件指挥员 / 系统管理员开放。
"""

import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_admin_user, get_db, get_required_user
from yuxi.services.police_service import _canonical_audit_string
from yuxi.storage.postgres.models_business import User
from yuxi.storage.postgres.models_police import CaseMember, PoliceAuditLog

audit_router = APIRouter(prefix="/police/audit", tags=["police-audit"])

# 视为「异常/敏感」的操作类型（用于审计概览的异常计数）
ANOMALY_ACTIONS = {"reject", "delete"}


async def _is_case_commander_or_admin(db: AsyncSession, user: User, case_id: int) -> bool:
    if user.role in ("admin", "superadmin"):
        return True
    row = await db.execute(
        select(CaseMember).where(
            CaseMember.case_id == case_id,
            CaseMember.user_id == user.id,
            CaseMember.role == "commander",
        )
    )
    return row.scalar_one_or_none() is not None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"非法时间格式: {value}")


@audit_router.get("/stats")
async def get_audit_stats(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """审计概览统计：今日操作数 / 异常操作数 / 最近事件 (top5)。供数据总览卡片使用。"""
    from yuxi.utils.datetime_utils import utc_now_naive

    start_of_day = utc_now_naive().replace(hour=0, minute=0, second=0, microsecond=0)

    today_ops = await db.scalar(
        select(func.count(PoliceAuditLog.id)).where(PoliceAuditLog.created_at >= start_of_day)
    )
    anomaly_ops = await db.scalar(
        select(func.count(PoliceAuditLog.id)).where(PoliceAuditLog.action.in_(ANOMALY_ACTIONS))
    )
    recent_rows = (
        await db.execute(
            select(PoliceAuditLog).order_by(PoliceAuditLog.id.desc()).limit(5)
        )
    ).scalars().all()

    recent_events = [
        {
            "id": r.id,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "user_name": r.user_name,
            "case_id": r.case_id,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_rows
    ]

    return {
        "code": 0,
        "message": "success",
        "data": {
            "today_ops": int(today_ops or 0),
            "anomaly_ops": int(anomaly_ops or 0),
            "recent_events": recent_events,
        },
    }


@audit_router.get("/logs")
async def list_audit_logs(
    action: str | None = Query(None, description="操作类型过滤"),
    user_id: int | None = Query(None, description="操作人过滤"),
    case_id: int | None = Query(None, description="案件过滤"),
    resource_type: str | None = Query(None, description="资源类型过滤"),
    from_time: str | None = Query(None, alias="from", description="起始时间 ISO"),
    to_time: str | None = Query(None, alias="to", description="结束时间 ISO"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """全局审计日志查询（系统管理员）。支持多维过滤与分页。"""
    stmt = select(PoliceAuditLog)
    if action:
        stmt = stmt.where(PoliceAuditLog.action == action)
    if user_id is not None:
        stmt = stmt.where(PoliceAuditLog.user_id == user_id)
    if case_id is not None:
        stmt = stmt.where(PoliceAuditLog.case_id == case_id)
    if resource_type:
        stmt = stmt.where(PoliceAuditLog.resource_type == resource_type)
    frm = _parse_dt(from_time)
    if frm:
        stmt = stmt.where(PoliceAuditLog.created_at >= frm)
    to = _parse_dt(to_time)
    if to:
        stmt = stmt.where(PoliceAuditLog.created_at <= to)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        await db.execute(stmt.order_by(PoliceAuditLog.id.desc()).limit(limit).offset(offset))
    ).scalars().all()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": int(total or 0),
            "items": [r.to_dict() for r in rows],
        },
    }


@audit_router.get("/cases/{case_id}/logs")
async def list_case_audit_logs(
    case_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """案件维度审计视图（案件指挥员 / 系统管理员）。"""
    if not await _is_case_commander_or_admin(db, current_user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要案件指挥员或管理员权限")

    stmt = select(PoliceAuditLog).where(PoliceAuditLog.case_id == case_id)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        await db.execute(stmt.order_by(PoliceAuditLog.id.desc()).limit(limit).offset(offset))
    ).scalars().all()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": int(total or 0),
            "items": [r.to_dict() for r in rows],
        },
    }


@audit_router.post("/verify")
async def verify_audit_chain(
    limit: int = Query(5000, ge=1, le=50000, description="校验的最大记录数"),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """审计哈希链校验：重算每条记录的 record_hash 并验证 prev_hash 链接是否连续。

    历史遗留记录（record_hash 为 NULL）不参与链校验，仅计入 legacy_count。
    """
    rows = (
        await db.execute(
            select(PoliceAuditLog).order_by(PoliceAuditLog.id.asc()).limit(limit)
        )
    ).scalars().all()

    checked = 0
    legacy_count = 0
    broken_at = None
    prev_record_hash = None

    for r in rows:
        if not r.record_hash:
            legacy_count += 1
            prev_record_hash = r.record_hash  # None
            continue
        # prev_hash 必须指向上一条（含遗留）记录的 record_hash
        if r.prev_hash != prev_record_hash:
            broken_at = r.id
            break
        recomputed = hashlib.sha256(
            _canonical_audit_string(
                action=r.action,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                case_id=r.case_id,
                user_id=r.user_id,
                details=r.details,
                ip=r.ip_address,
                ua=r.user_agent,
                # 归一化为 naive ISO，避免 TIMESTAMPTZ 读回时携带 +00:00 导致哈希不一致
                created_at_iso=(r.created_at.replace(tzinfo=None).isoformat() if r.created_at else ""),
                prev_hash=r.prev_hash,
            ).encode("utf-8")
        ).hexdigest()
        if recomputed != r.record_hash:
            broken_at = r.id
            break
        checked += 1
        prev_record_hash = r.record_hash

    return {
        "code": 0,
        "message": "success",
        "data": {
            "ok": broken_at is None,
            "checked": checked,
            "legacy_count": legacy_count,
            "broken_at": broken_at,
        },
    }
