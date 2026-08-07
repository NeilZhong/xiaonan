"""★ 任务截止提醒服务

职责：
  1. 扫描未关闭且有 due_date 的任务，产出「即将到期 / 已逾期」提醒
  2. 向任务执行人（民警）与案件指挥员写入站内通知（police_notifications）
  3. 供 ARQ 定时任务（cron）每日调用；best-effort，失败不阻塞主流程

触发方式（run_worker.WorkerSettings.cron_jobs 注册）：
  - police_due_reminder 每天扫描一次
"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_police import (
    CaseMember,
    PoliceNotification,
    PoliceTask,
    TaskAssignee,
)

# 视为「已结束/关闭」的状态，不参与到期提醒
_CLOSED_STATUS = {"completed", "cancelled", "terminated"}
# 默认提前提醒天数
DEFAULT_LEAD_DAYS = 1


class PoliceDueReminderService:
    async def scan_and_notify(self, lead_days: int = DEFAULT_LEAD_DAYS) -> int:
        """扫描全部未关闭且有截止时间的任务，写入到期提醒通知。返回写入条数。

        - 已逾期任务 → type=overdue，通知执行人与指挥员
        - lead_days 内到期 → type=due_soon，通知执行人与指挥员
        - 已关闭任务不提醒
        """
        now = datetime.utcnow()
        today = now.date()
        due_threshold = now + timedelta(days=lead_days)

        async with pg_manager.get_async_session_context() as session:
            tasks = (
                await session.execute(
                    select(PoliceTask).where(
                        PoliceTask.due_date.is_not(None),
                        PoliceTask.status.notin_(_CLOSED_STATUS),
                    )
                )
            ).scalars().all()
            if not tasks:
                return 0

            # 一次性拉取相关执行人 / 案件成员，避免逐任务查询
            task_ids = [t.id for t in tasks]
            case_ids = list({t.case_id for t in tasks if t.case_id})
            assignee_rows = (
                await session.execute(
                    select(TaskAssignee).where(
                        TaskAssignee.task_id.in_(task_ids),
                        TaskAssignee.assignee_type == "human",
                    )
                )
            ).scalars().all()
            member_rows = (
                await session.execute(
                    select(CaseMember).where(
                        CaseMember.case_id.in_(case_ids),
                        CaseMember.role == "commander",
                    )
                )
            ).scalars().all() if case_ids else []

            # 任务 → 接收人（执行人 + 指挥员，去重）
            recipient_map: dict[int, set[int]] = {}
            for a in assignee_rows:
                if a.assignee_id:
                    recipient_map.setdefault(a.task_id, set()).add(a.assignee_id)
            for m in member_rows:
                recipient_map.setdefault(m.case_id, set()).add(m.user_id)

            written = 0
            for t in tasks:
                due = t.due_date
                if due < now:
                    rtype, level = "overdue", "已逾期"
                    content = f"任务「{t.title}」已逾期，应完成于 {due.strftime('%Y-%m-%d')}，请尽快处理。"
                elif due <= due_threshold:
                    rtype, level = "due_soon", "即将到期"
                    days_left = (due.date() - today).days
                    content = f"任务「{t.title}」将于 {days_left} 天内到期（{due.strftime('%Y-%m-%d')}），请及时处理。"
                else:
                    continue

                # 直接接收人：任务执行人 + 该案指挥员
                recipients = set()
                if t.assignee_id:
                    recipients.add(t.assignee_id)
                recipients.update(recipient_map.get(t.id, set()))
                recipients.update(recipient_map.get(t.case_id, set()))

                for uid in recipients:
                    if not uid:
                        continue
                    session.add(PoliceNotification(
                        user_id=uid,
                        case_id=t.case_id,
                        task_id=t.id,
                        type=rtype,
                        title=f"{level}：{t.title}",
                        content=content,
                    ))
                    written += 1
            await session.commit()
            return written

    async def list_notifications(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """查询某用户的站内通知（未读优先，按时间倒序）。"""
        async with pg_manager.get_async_session_context() as session:
            rows = (
                await session.execute(
                    select(PoliceNotification)
                    .where(PoliceNotification.user_id == user_id)
                    .order_by(PoliceNotification.read_at.is_(None).desc(), PoliceNotification.created_at.desc())
                    .limit(limit)
                )
            ).scalars().all()
            return [r.to_dict() for r in rows]

    async def mark_read(self, user_id: int, notification_id: int) -> bool:
        """标记单条通知已读。"""
        async with pg_manager.get_async_session_context() as session:
            row = (
                await session.execute(
                    select(PoliceNotification).where(
                        PoliceNotification.id == notification_id,
                        PoliceNotification.user_id == user_id,
                    )
                )
            ).scalar_one_or_none()
            if not row:
                return False
            row.read_at = datetime.utcnow()
            await session.commit()
            return True

    async def unread_count(self, user_id: int) -> int:
        """未读通知数（工作台角标用）。"""
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(PoliceNotification.id).where(
                    PoliceNotification.user_id == user_id,
                    PoliceNotification.read_at.is_(None),
                )
            )
            return len(result.all())


police_due_reminder_service = PoliceDueReminderService()
