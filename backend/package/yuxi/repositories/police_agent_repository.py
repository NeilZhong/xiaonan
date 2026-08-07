"""★ 数字警员仓储 — CRUD + 工作统计 + SOP + 运行记录

融合 StaffDeck 数字员工概念：每位数字警员有档案、能力、工作记录。

单表化说明：数字警员即 yuxi 一等智能体，所有档案/可见性/审批数据统一存放于
yuxi 原生 agents 表（models_business.Agent）。本仓储直接操作 Agent 模型，
可见性判断复用 agent_repository.user_can_access_agent（share_config 体系）。
"""

from typing import Any
from uuid import uuid4

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select

from yuxi.storage.postgres.models_business import Agent
from yuxi.storage.postgres.models_police import (
    PoliceAgentRun,
    PoliceAgentComment,
    PoliceSOP,
)
from yuxi.repositories.agent_repository import user_can_access_agent
from yuxi.repositories.police_binding_repository import agent_binding_repository
from yuxi.storage.postgres.manager import pg_manager
from yuxi.utils.datetime_utils import utc_now_naive
from yuxi.utils import logger


class PoliceAgentRepository:
    """数字警员仓储（统一操作 agents 表）"""

    async def get_by_id(self, agent_id: int) -> Agent | None:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(Agent).where(Agent.id == agent_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Agent | None:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(Agent).where(Agent.slug == slug)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_badge_number(self, badge_number: str) -> Agent | None:
        """按工号查询数字警员（大小写不敏感）。"""
        async with pg_manager.get_async_session_context() as session:
            stmt = select(Agent).where(func.lower(Agent.badge_number) == func.lower(badge_number))
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def resolve_by_identifier(self, identifier: str | int) -> Agent | None:
        """按多种标识符解析数字警员档案（单一数据源 agents 表）：

        - 纯数字 → agents 主键 id
        - 工号（大小写不敏感，如 DA-005 / da-005）→ badge_number
        - yuxi 智能体 slug（如 officer-5 / da-005）→ agents.slug

        前端统一以 agents.slug 作为智能体 id，故 share/approve 等路由需支持解析，
        否则 FastAPI 把 slug 当作 int 主键会直接 422。
        """
        identifier = str(identifier).strip()
        if not identifier:
            return None
        if identifier.isdigit():
            return await self.get_by_id(int(identifier))
        agent = await self.get_by_badge_number(identifier)
        if agent:
            return agent
        return await self.get_by_slug(identifier)

    async def list_agents(
        self, *, type: str | None = None, status: str | None = None,
        keyword: str | None = None, category: str | None = None,
        page: int = 1, page_size: int = 50, current_user: Any = None,
    ) -> tuple[list[Agent], int]:
        async with pg_manager.get_async_session_context() as session:
            # 数字警员 = 非协助伙伴（is_subagent）且非平台内置智能体（is_system）。
            # 早期以 category 是否为空充当该判据，导致「功能分类」被迫成为必填项，现改为显式标记。
            stmt = select(Agent).where(Agent.is_subagent.is_(False), Agent.is_system.is_(False))
            if type:
                stmt = stmt.where(Agent.agent_type == type)
            if status:
                stmt = stmt.where(Agent.status == status)
            if category:
                stmt = stmt.where(Agent.category == category)
            if keyword:
                stmt = stmt.where(Agent.name.ilike(f"%{keyword}%"))
            stmt = stmt.order_by(Agent.id.desc())
            result = await session.execute(stmt)
            all_agents = list(result.scalars().all())
        # 可见性过滤（复用 yuxi 共享/审批体系，无 SQL 层可见性列）
        if current_user is not None:
            # P2c：用户通过「添加」建立的连接（active）也视为可访问（不复制警员，仅授权）。
            # 批量取一次连接集合，避免在列表循环里逐条查库（N+1）。
            connected_ids = await agent_binding_repository.list_connected_agent_ids(current_user.id)
            all_agents = [
                a for a in all_agents
                if user_can_access_agent(current_user, a) or a.id in connected_ids
            ]
        total = len(all_agents)
        start = (page - 1) * page_size
        return all_agents[start:start + page_size], total

    async def list_pending_agents(self, *, page: int = 1, page_size: int = 50) -> tuple[list[Agent], int]:
        """待审批（全局共享申请）列表：approval_status='pending'。"""
        async with pg_manager.get_async_session_context() as session:
            stmt = select(Agent).where(Agent.approval_status == "pending").order_by(Agent.id.desc())
            count_stmt = select(func.count()).select_from(Agent).where(Agent.approval_status == "pending")
            total = (await session.execute(count_stmt)).scalar() or 0
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
            result = await session.execute(stmt)
            return list(result.scalars().all()), total

    async def create(self, data: dict[str, Any]) -> Agent:
        async with pg_manager.get_async_session_context() as session:
            data = dict(data)
            data.pop("is_template", None)  # 预设遗留字段，Agent 模型无此列
            data.setdefault("pics", [])
            data.setdefault("config_json", {"context": {}})
            data.setdefault(
                "share_config",
                {"access_level": "user", "department_ids": [], "user_uids": []},
            )
            # 先置临时 slug，插入拿到自增 id 后再改为 officer-{id}（slug 与警号解耦）
            data["slug"] = f"officer-{uuid4().hex[:8]}"
            agent = Agent(**data)
            session.add(agent)
            await session.flush()
            agent.slug = f"officer-{agent.id}"
            await session.commit()
            await session.refresh(agent)
            return agent

    async def update(self, agent_id: int, data: dict[str, Any]) -> Agent | None:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(Agent).where(Agent.id == agent_id)
            result = await session.execute(stmt)
            agent = result.scalar_one_or_none()
            if not agent:
                return None
            for k, v in data.items():
                if hasattr(agent, k) and v is not None:
                    setattr(agent, k, v)
            await session.commit()
            await session.refresh(agent)
            return agent

    async def delete(self, agent_id: int) -> bool:
        async with pg_manager.get_async_session_context() as session:
            # 先清理关联的运行记录与留言（agents 主键被 police 关联表外键引用，无级联）
            await session.execute(sa_delete(PoliceAgentRun).where(PoliceAgentRun.agent_id == agent_id))
            await session.execute(sa_delete(PoliceAgentComment).where(PoliceAgentComment.agent_id == agent_id))
            agent = await session.get(Agent, agent_id)
            if not agent:
                return False
            await session.delete(agent)
            await session.commit()
            return True

    async def update_work_stats(self, agent_id: int, stats: dict[str, Any]) -> bool:
        """更新数字警员工作统计"""
        async with pg_manager.get_async_session_context() as session:
            stmt = select(Agent).where(Agent.id == agent_id)
            result = await session.execute(stmt)
            agent = result.scalar_one_or_none()
            if not agent:
                return False
            current = agent.work_stats or {}
            current.update(stats)
            agent.work_stats = current
            await session.commit()
            return True

    async def add_growth_event(self, agent_id: int, event: str, description: str) -> bool:
        """添加成长记录事件"""
        async with pg_manager.get_async_session_context() as session:
            stmt = select(Agent).where(Agent.id == agent_id)
            result = await session.execute(stmt)
            agent = result.scalar_one_or_none()
            if not agent:
                return False
            log = agent.growth_log or []
            log.append({
                "date": utc_now_naive().isoformat(),
                "event": event,
                "description": description,
            })
            agent.growth_log = log
            await session.commit()
            return True

    async def list_runs(
        self, *, agent_id: int | None = None, case_id: int | None = None,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[PoliceAgentRun], int]:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentRun)
            count_stmt = select(func.count()).select_from(PoliceAgentRun)

            if agent_id:
                stmt = stmt.where(PoliceAgentRun.agent_id == agent_id)
                count_stmt = count_stmt.where(PoliceAgentRun.agent_id == agent_id)
            if case_id:
                stmt = stmt.where(PoliceAgentRun.case_id == case_id)
                count_stmt = count_stmt.where(PoliceAgentRun.case_id == case_id)

            total = (await session.execute(count_stmt)).scalar() or 0
            stmt = stmt.order_by(PoliceAgentRun.id.desc()).offset(
                (page - 1) * page_size
            ).limit(page_size)
            result = await session.execute(stmt)
            runs = list(result.scalars().all())
            return runs, total

    async def create_run(self, data: dict[str, Any]) -> PoliceAgentRun:
        async with pg_manager.get_async_session_context() as session:
            run = PoliceAgentRun(**data)
            session.add(run)
            await session.commit()
            await session.refresh(run)
            return run

    async def update_run(self, run_id: int, data: dict[str, Any]) -> PoliceAgentRun | None:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentRun).where(PoliceAgentRun.id == run_id)
            result = await session.execute(stmt)
            run = result.scalar_one_or_none()
            if not run:
                return None
            for k, v in data.items():
                if hasattr(run, k) and v is not None:
                    setattr(run, k, v)
            await session.commit()
            await session.refresh(run)
            return run

    # ── SOP 管理 ──────────────────────────────────────────────

    async def list_sops(
        self, *, agent_type: str | None = None, category: str | None = None,
    ) -> list[PoliceSOP]:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceSOP)
            if agent_type:
                stmt = stmt.where(PoliceSOP.agent_type == agent_type)
            if category:
                stmt = stmt.where(PoliceSOP.category == category)
            stmt = stmt.order_by(PoliceSOP.id.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_sop(self, sop_id: int) -> PoliceSOP | None:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceSOP).where(PoliceSOP.id == sop_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create_sop(self, data: dict[str, Any]) -> PoliceSOP:
        async with pg_manager.get_async_session_context() as session:
            sop = PoliceSOP(**data)
            session.add(sop)
            await session.commit()
            await session.refresh(sop)
            return sop

    async def update_sop(self, sop_id: int, data: dict[str, Any]) -> PoliceSOP | None:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceSOP).where(PoliceSOP.id == sop_id)
            result = await session.execute(stmt)
            sop = result.scalar_one_or_none()
            if not sop:
                return None
            for k, v in data.items():
                if hasattr(sop, k) and v is not None:
                    setattr(sop, k, v)
            await session.commit()
            await session.refresh(sop)
            return sop

    async def update_share(self, agent_id: int, **kwargs) -> bool:
        """更新智能体的共享字段（share_config / approval_status 等）"""
        async with pg_manager.get_async_session_context() as session:
            agent = await session.get(Agent, agent_id)
            if not agent:
                return False
            for k, v in kwargs.items():
                if hasattr(agent, k):
                    setattr(agent, k, v)
            await session.commit()
            return True

    # ── 留言板 ──────────────────────────────────────────────

    async def list_comments(self, *, agent_id: int, page: int = 1, page_size: int = 50) -> tuple[list[PoliceAgentComment], int]:
        """查询智能体的留言列表，按创建时间倒序"""
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentComment).where(PoliceAgentComment.agent_id == agent_id)
            count_stmt = select(func.count()).select_from(PoliceAgentComment).where(
                PoliceAgentComment.agent_id == agent_id
            )
            total = (await session.execute(count_stmt)).scalar() or 0
            stmt = stmt.order_by(PoliceAgentComment.created_at.desc()).offset(
                (page - 1) * page_size
            ).limit(page_size)
            result = await session.execute(stmt)
            comments = list(result.scalars().all())
            return comments, total

    async def create_comment(self, agent_id: int, user_id: int | None, content: str, rating: int | None = None) -> PoliceAgentComment:
        """创建留言"""
        async with pg_manager.get_async_session_context() as session:
            comment = PoliceAgentComment(agent_id=agent_id, user_id=user_id, content=content, rating=rating)
            session.add(comment)
            await session.commit()
            await session.refresh(comment)
            return comment

    async def delete_comment(self, comment_id: int, agent_id: int) -> bool:
        """删除留言（需匹配 agent_id 防止越权）"""
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentComment).where(
                PoliceAgentComment.id == comment_id,
                PoliceAgentComment.agent_id == agent_id
            )
            result = await session.execute(stmt)
            comment = result.scalar_one_or_none()
            if not comment:
                return False
            await session.delete(comment)
            await session.commit()
            return True


police_agent_repository = PoliceAgentRepository()
