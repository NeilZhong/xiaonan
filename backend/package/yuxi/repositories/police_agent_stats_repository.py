"""★ 数字警员真实工作统计仓储（公安业务扩展，不覆盖 yuxi 核心模块）

死数据根因：agents.work_stats 是静态 JSON 快照字段，update_work_stats()
从未被任何业务流程调用，导致档案页/卡片的累计对话、今日对话、好评率、
差评数等永远是空值。

本仓储改为在读取时从真实业务表实时聚合：
  - conversations          按 agent slug 关联 → 累计/今日对话数
  - message_feedbacks      rating=like/dislike → 好评/差评数与好评率
  - police_agent_runs      按 agent_id 关联    → 累计/今日完成任务数

统计口径：
  - 累计对话：该 slug 下非删除状态的会话数
  - 今日对话：created_at 落在「今日（Asia/Shanghai 折算为 UTC 区间）」的会话数
  - 完成任务：police_agent_runs 中 status=completed 的记录数（含今日口径）
  - 好评/差评：会话消息上的 like/dislike 反馈总数
  - 好评率：like / (like + dislike) * 100，无反馈时返回 None（前端显示 —）
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Iterable

from sqlalchemy import case as sa_case, func, select

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_business import (
    Conversation,
    Message,
    MessageFeedback,
)
from yuxi.storage.postgres.models_police import PoliceAgentRun
from yuxi.utils.datetime_utils import SHANGHAI_TZ, ensure_utc


def _today_utc_range() -> tuple[dt.datetime, dt.datetime]:
    """返回「今日」对应的 UTC 半开区间 [start, end)。

    以 Asia/Shanghai 当地日期为准折算为 UTC：本地 00:00 即当日起点，
    次日本地 00:00 为终点。数据库存储 naive UTC，区间端点同样以 naive UTC 传入。
    """
    local_today = dt.datetime.now(SHANGHAI_TZ).date()
    start_local = dt.datetime.combine(local_today, dt.time.min, tzinfo=SHANGHAI_TZ)
    end_local = start_local + dt.timedelta(days=1)
    start_utc = ensure_utc(start_local).replace(tzinfo=None)
    end_utc = ensure_utc(end_local).replace(tzinfo=None)
    return start_utc, end_utc


class PoliceAgentStatsRepository:
    """数字警员实时工作统计聚合（只读，GROUP BY 批量，避免 N+1）"""

    # ── 内部：单表 GROUP BY 聚合 ──────────────────────────────
    async def _conv_counts_by_slug(self, slugs: list[str], start_utc, end_utc) -> dict[str, dict[str, int]]:
        """按 slug 聚合累计/今日对话数。"""
        if not slugs:
            return {}
        in_today = (
            (Conversation.created_at >= start_utc) & (Conversation.created_at < end_utc)
        )
        async with pg_manager.get_async_session_context() as session:
            rows = (
                await session.execute(
                    select(
                        Conversation.agent_id.label("slug"),
                        func.count(Conversation.id).label("total"),
                        func.count(sa_case((in_today, 1), else_=None)).label("daily"),
                    )
                    .where(
                        Conversation.agent_id.in_(slugs),
                        Conversation.status != "deleted",
                    )
                    .group_by(Conversation.agent_id)
                )
            ).all()
        return {
            r.slug: {"total": int(r.total or 0), "daily": int(r.daily or 0)} for r in rows
        }

    async def _run_counts_by_agent(self, agent_ids: list[int], start_utc, end_utc) -> dict[int, dict[str, int]]:
        """按 agent_id 聚合累计/今日完成任务数（police_agent_runs）。"""
        if not agent_ids:
            return {}
        in_today = (
            (PoliceAgentRun.created_at >= start_utc) & (PoliceAgentRun.created_at < end_utc)
        )
        async with pg_manager.get_async_session_context() as session:
            rows = (
                await session.execute(
                    select(
                        PoliceAgentRun.agent_id.label("agent_id"),
                        func.count(PoliceAgentRun.id).label("total"),
                        func.count(sa_case((in_today, 1), else_=None)).label("daily"),
                    )
                    .where(
                        PoliceAgentRun.agent_id.in_(agent_ids),
                        PoliceAgentRun.status == "completed",
                    )
                    .group_by(PoliceAgentRun.agent_id)
                )
            ).all()
        return {
            int(r.agent_id): {"total": int(r.total or 0), "daily": int(r.daily or 0)}
            for r in rows
        }

    async def _feedback_counts_by_slug(self, slugs: list[str], start_utc, end_utc) -> dict[str, dict[str, int]]:
        """按 slug 聚合消息反馈 like/dislike（累计 + 今日）。"""
        if not slugs:
            return {}
        is_like = sa_case((MessageFeedback.rating == "like", 1), else_=0)
        is_dislike = sa_case((MessageFeedback.rating == "dislike", 1), else_=0)
        in_today = (
            (MessageFeedback.created_at >= start_utc) & (MessageFeedback.created_at < end_utc)
        )
        async with pg_manager.get_async_session_context() as session:
            rows = (
                await session.execute(
                    select(
                        Conversation.agent_id.label("slug"),
                        func.sum(is_like).label("likes"),
                        func.sum(is_dislike).label("dislikes"),
                        func.sum(sa_case((in_today & (MessageFeedback.rating == "like"), 1), else_=0)).label("daily_likes"),
                        func.sum(sa_case((in_today & (MessageFeedback.rating == "dislike"), 1), else_=0)).label("daily_dislikes"),
                    )
                    .select_from(MessageFeedback)
                    .join(Message, MessageFeedback.message_id == Message.id)
                    .join(Conversation, Message.conversation_id == Conversation.id)
                    .where(
                        Conversation.agent_id.in_(slugs),
                        Conversation.status != "deleted",
                    )
                    .group_by(Conversation.agent_id)
                )
            ).all()
        return {
            r.slug: {
                "likes": int(r.likes or 0),
                "dislikes": int(r.dislikes or 0),
                "daily_likes": int(r.daily_likes or 0),
                "daily_dislikes": int(r.daily_dislikes or 0),
            }
            for r in rows
        }

    # ── 对外：单个 / 批量 ────────────────────────────────────
    async def compute_daily_trend(
        self, agent_id: int, agent_slug: str, days: int = 14
    ) -> list[dict[str, Any]]:
        """按天聚合近 N 天对话/任务趋势（Asia/Shanghai 日界）。

        返回 [{date: 'YYYY-MM-DD', conversations: n, tasks: m}]，无数据的天补零，
        供档案页「对话与任务趋势」图表使用（此前图表把任务运行误判为对话）。
        """
        start_utc, _ = _today_utc_range()
        start_utc = start_utc - dt.timedelta(days=days - 1)
        local_today = dt.datetime.now(SHANGHAI_TZ).date()

        async with pg_manager.get_async_session_context() as session:
            conv_rows = (
                await session.execute(
                    select(
                        func.date(Conversation.created_at).label("d"),
                        func.count(Conversation.id).label("n"),
                    )
                    .where(
                        Conversation.agent_id == agent_slug,
                        Conversation.status != "deleted",
                        Conversation.created_at >= start_utc,
                    )
                    .group_by(func.date(Conversation.created_at))
                )
            ).all()
            run_rows = (
                await session.execute(
                    select(
                        func.date(PoliceAgentRun.created_at).label("d"),
                        func.count(PoliceAgentRun.id).label("n"),
                    )
                    .where(
                        PoliceAgentRun.agent_id == agent_id,
                        PoliceAgentRun.status == "completed",
                        PoliceAgentRun.created_at >= start_utc,
                    )
                    .group_by(func.date(PoliceAgentRun.created_at))
                )
            ).all()

        conv_map = {r.d: int(r.n or 0) for r in conv_rows}
        run_map = {r.d: int(r.n or 0) for r in run_rows}
        trend = []
        for offset in range(days):
            day = local_today - dt.timedelta(days=days - 1 - offset)
            trend.append(
                {
                    "date": day.isoformat(),
                    "conversations": conv_map.get(day, 0),
                    "tasks": run_map.get(day, 0),
                }
            )
        return trend

    async def compute_batch_stats(
        self, agents: Iterable[Any]
    ) -> dict[int, dict[str, Any]]:
        """批量计算多个智能体的实时统计。

        agents: 可迭代的 Agent ORM 或 dict（需含 id 与 slug）。
        返回 {agent_id: stats_dict}，字段与档案页前端读取的 work_stats 对齐。
        """
        agent_list = []
        for a in agents:
            aid = a.id if hasattr(a, "id") else a.get("id")
            slug = a.slug if hasattr(a, "slug") else a.get("slug")
            if aid is None or not slug:
                continue
            agent_list.append((int(aid), str(slug)))
        if not agent_list:
            return {}

        slugs = [s for _, s in agent_list]
        ids = [i for i, _ in agent_list]
        start_utc, end_utc = _today_utc_range()

        conv_map = await self._conv_counts_by_slug(slugs, start_utc, end_utc)
        run_map = await self._run_counts_by_agent(ids, start_utc, end_utc)
        fb_map = await self._feedback_counts_by_slug(slugs, start_utc, end_utc)

        result: dict[int, dict[str, Any]] = {}
        for aid, slug in agent_list:
            conv = conv_map.get(slug, {"total": 0, "daily": 0})
            runs = run_map.get(aid, {"total": 0, "daily": 0})
            fb = fb_map.get(slug, {"likes": 0, "dislikes": 0, "daily_likes": 0, "daily_dislikes": 0})
            likes, dislikes = fb["likes"], fb["dislikes"]
            result[aid] = {
                "total_conversations": conv["total"],
                "daily_conversations": conv["daily"],
                "total_tasks": runs["total"],
                "daily_tasks": runs["daily"],
                "like_count": likes,
                "dislike_count": dislikes,
                "feedback_positive": round(likes / (likes + dislikes) * 100, 1) if (likes + dislikes) > 0 else None,
                "feedback_negative": dislikes,
                "daily_positive": fb["daily_likes"],
                "daily_negative": fb["daily_dislikes"],
            }
        return result

    async def compute_agent_stats(self, agent_id: int, agent_slug: str) -> dict[str, Any]:
        """计算单个智能体的实时统计（内部复用批量实现）。"""
        stats_map = await self.compute_batch_stats([{"id": agent_id, "slug": agent_slug}])
        return stats_map.get(int(agent_id), {})


police_agent_stats_repository = PoliceAgentStatsRepository()
