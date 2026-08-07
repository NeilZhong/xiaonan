"""★ 案件任务统计服务

按案件聚合四类数据（对应统计 Tab 需求）：
  1. 概览指标：总数 / 已完成 / 未完成 / 已逾期 / 待认领 / 时间待定 / 今日到期 / 逾期完成
  2. 人机分配占比（饼图）：基于 TaskAssignee(role=executor) 的 assignee_type 计数
  3. 燃尽图：按 created_at~今天 每日 completed 累计 / remaining
  4. 风险汇总：诉讼时效 / 程序合规 / 法定时限，由 due_date / require_approval 推导，
     不新建 Risk 表（符合 Phase 0「风险作为 stats 计算结果」设计）。
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yuxi.storage.postgres.models_police import PoliceTask, TaskAssignee

# 视为「已结束/关闭」的状态，不参与逾期 / 剩余计算
_CLOSED_STATUS = {"completed", "cancelled", "terminated"}
# 视为「已提交完成」的状态（含待审核 review）——燃尽图完成口径，避免 complete() 仅置 review 导致直线
_DONE_STATUS = {"completed", "review"}


def _as_utc(dt: datetime | None) -> datetime | None:
    """统一为 aware UTC：naive 视为 UTC（DB TIMESTAMP 无时区列写入的是 utc_now_naive）。

    避免 aware(TIMESTAMPTZ) 与 naive(TIMESTAMP) 混合比较抛 TypeError。
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class PoliceCaseStatsService:
    async def get_case_stats(self, case_id: int, db: AsyncSession) -> dict[str, Any]:
        # ── 拉取案件全部任务 ──
        tasks = (
            await db.execute(select(PoliceTask).where(PoliceTask.case_id == case_id))
        ).scalars().all()
        task_ids = [t.id for t in tasks]

        # ── 拉取执行人分配（role=executor）用于人机占比 ──
        executor_rows: list[TaskAssignee] = []
        if task_ids:
            executor_rows = (
                await db.execute(
                    select(TaskAssignee).where(
                        TaskAssignee.task_id.in_(task_ids),
                        TaskAssignee.role == "executor",
                    )
                )
            ).scalars().all()

        now = datetime.now(timezone.utc)
        today = now.date()

        # ── 概览指标 ──
        total = len(tasks)
        by_status: dict[str, int] = {}
        overdue = 0
        unclaimed = 0
        time_undetermined = 0
        due_today = 0
        overdue_completed = 0
        assigned = 0
        for t in tasks:
            by_status[t.status] = by_status.get(t.status, 0) + 1
            is_closed = t.status in _CLOSED_STATUS
            has_executor = any(r.task_id == t.id for r in executor_rows)
            if has_executor or t.assignee_id or t.assigned_at:
                assigned += 1
            if not has_executor and not t.assignee_id:
                unclaimed += 1
            if t.due_date:
                due = _as_utc(t.due_date)
                completed_at = _as_utc(t.completed_at)
                if not is_closed:
                    if due < now:
                        overdue += 1
                    elif due.date() == today:
                        due_today += 1
                    if completed_at and completed_at > due:
                        overdue_completed += 1
            elif not is_closed:
                time_undetermined += 1

        overview = {
            "total": total,
            "completed": by_status.get("completed", 0),
            "in_progress": by_status.get("in_progress", 0),
            "pending": by_status.get("pending", 0),
            "paused": by_status.get("paused", 0),
            "review": by_status.get("review", 0),
            "cancelled": by_status.get("cancelled", 0) + by_status.get("terminated", 0),
            "overdue": overdue,
            "unclaimed": unclaimed,
            "assigned": assigned,
            "time_undetermined": time_undetermined,
            "due_today": due_today,
            "overdue_completed": overdue_completed,
        }

        # ── 人机分配占比（饼图，按 executor 分配人次） ──
        human = sum(1 for r in executor_rows if r.assignee_type == "human")
        agent = sum(1 for r in executor_rows if r.assignee_type == "agent")
        worker_distribution = {
            "human": human,
            "agent": agent,
            "total_assignments": human + agent,
        }

        # ── 燃尽图 + 风险汇总 + 截止提醒 ──
        burndown = self._build_burndown(tasks, now)
        risks, risk_summary = self._build_risks(tasks, now, today)
        reminders = self._build_reminders(tasks, now, today)

        return {
            "overview": overview,
            "worker_distribution": worker_distribution,
            "burndown": burndown,
            "risks": risks,
            "risk_summary": risk_summary,
            "reminders": reminders,
        }

    @staticmethod
    def _build_burndown(tasks: list[PoliceTask], now: datetime) -> list[dict[str, Any]]:
        """按 created_at/assigned_at~今天生成每日已完成累计 / 剩余序列。

        完成口径为「已提交完成」（status ∈ _DONE_STATUS，含待审核 review），
        否则 complete() 将状态置为 review 的阶段不会被统计，曲线呈直线。
        """
        total = len(tasks)
        if total == 0:
            return []
        # 时间轴起点：优先取最早分配时间，否则取最早创建时间（历史任务无 assigned_at 的兜底）
        starts = [
            _as_utc(t.assigned_at or t.created_at)
            for t in tasks
            if (t.assigned_at or t.created_at)
        ]
        start = min(starts).date() if starts else now.date()
        end = now.date()
        if (end - start).days > 60:
            start = end - timedelta(days=60)  # 最多回溯 60 天，避免过长

        completed_by_date: dict = {}
        for t in tasks:
            ref_time = _as_utc(t.completed_at) or _as_utc(t.assigned_at) or _as_utc(t.created_at)
            if t.status in _DONE_STATUS and ref_time:
                d = ref_time.date()
                completed_by_date[d] = completed_by_date.get(d, 0) + 1

        series: list[dict[str, Any]] = []
        cum = 0
        cur = start
        while cur <= end:
            cum += completed_by_date.get(cur, 0)
            series.append({
                "date": cur.isoformat(),
                "completed": cum,
                "remaining": total - cum,
            })
            cur += timedelta(days=1)
        return series

    @staticmethod
    def _build_risks(
        tasks: list[PoliceTask], now: datetime, today
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """推导诉讼时效 / 程序合规 / 法定时限风险，按等级排序取前 10。"""
        risks: list[dict[str, Any]] = []
        for t in tasks:
            if t.status in _CLOSED_STATUS:
                continue
            if t.due_date:
                due = _as_utc(t.due_date)
                if due < now:
                    risks.append({
                        "type": "legal_time_limit",
                        "level": "high",
                        "task_id": t.id,
                        "title": t.title,
                        "detail": f"任务已超法定/计划时限（应完成于 {due.strftime('%Y-%m-%d')}）",
                    })
                elif due.date() == today:
                    risks.append({
                        "type": "due_soon",
                        "level": "medium",
                        "task_id": t.id,
                        "title": t.title,
                        "detail": f"任务今日到期（{due.strftime('%Y-%m-%d')}）",
                    })
                else:
                    days_left = (due.date() - today).days
                    if 0 < days_left <= 3:
                        risks.append({
                            "type": "due_soon",
                            "level": "low",
                            "task_id": t.id,
                            "title": t.title,
                            "detail": f"任务将于 {days_left} 天内到期（{due.strftime('%Y-%m-%d')}）",
                        })
            # 程序合规：含 AI 产出但未审查签字
            if t.require_approval == 1 and t.status == "completed" and not t.reviewed_at:
                risks.append({
                    "type": "procedure_compliance",
                    "level": "high",
                    "task_id": t.id,
                    "title": t.title,
                    "detail": "任务含 AI 产出但未经民警审核签字",
                })

        level_rank = {"high": 0, "medium": 1, "low": 2}
        risks.sort(key=lambda r: level_rank.get(r["level"], 3))
        risks = risks[:10]
        summary = {"high": 0, "medium": 0, "low": 0}
        for r in risks:
            summary[r["level"]] = summary.get(r["level"], 0) + 1
        return risks, summary

    @staticmethod
    def _build_reminders(
        tasks: list[PoliceTask], now: datetime, today, lead_days: int = 1
    ) -> list[dict[str, Any]]:
        """扫描未关闭且有 due_date 的任务，产出「即将到期 / 已逾期」提醒清单。

        lead_days 为提前提醒天数（默认 1 天）；仅面向未关闭任务，
        已关闭（completed/cancelled/terminated）不提醒。
        """
        reminders: list[dict[str, Any]] = []
        for t in tasks:
            if t.status in _CLOSED_STATUS or not t.due_date:
                continue
            due = _as_utc(t.due_date)
            if due < now:
                reminders.append({
                    "type": "overdue",
                    "level": "high",
                    "task_id": t.id,
                    "title": t.title,
                    "due_date": due.isoformat(),
                    "detail": f"任务已逾期（应完成于 {due.strftime('%Y-%m-%d')}）",
                })
            else:
                days_left = (due.date() - today).days
                if days_left <= lead_days:
                    reminders.append({
                        "type": "due_soon",
                        "level": "medium",
                        "task_id": t.id,
                        "title": t.title,
                        "due_date": due.isoformat(),
                        "days_left": days_left,
                        "detail": f"任务将于 {days_left} 天内到期（{due.strftime('%Y-%m-%d')}）",
                    })
        # 逾期置顶，其次到期日近
        reminders.sort(key=lambda r: (0 if r["type"] == "overdue" else 1, r.get("days_left", 0)))
        return reminders


police_case_stats_service = PoliceCaseStatsService()
