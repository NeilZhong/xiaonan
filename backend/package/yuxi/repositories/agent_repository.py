"""★ 数字警员仓储 — CRUD + 工作统计 + SOP + 运行记录

融合 StaffDeck 数字员工概念：每位数字警员有档案、能力、工作记录。
"""

from typing import Any

from sqlalchemy import func, select

from yuxi.storage.postgres.models_police import (
    PoliceAgent,
    PoliceAgentRun,
    PoliceSOP,
)
from yuxi.utils.datetime_utils import utc_now_naive
from yuxi.utils import logger


class AgentRepository:
    """数字警员仓储"""

    async def get_by_id(self, agent_id: int) -> PoliceAgent | None:
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
            stmt = select(PoliceAgent).where(PoliceAgent.id == agent_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_agents(
        self,
        *,
        type: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PoliceAgent], int]:
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
            stmt = select(PoliceAgent)
            count_stmt = select(func.count()).select_from(PoliceAgent)

            if type:
                stmt = stmt.where(PoliceAgent.type == type)
                count_stmt = count_stmt.where(PoliceAgent.type == type)
            if status:
                stmt = stmt.where(PoliceAgent.status == status)
                count_stmt = count_stmt.where(PoliceAgent.status == status)
            if keyword:
                pattern = f"%{keyword}%"
                stmt = stmt.where(PoliceAgent.name.ilike(pattern))
                count_stmt = count_stmt.where(PoliceAgent.name.ilike(pattern))

            total = (await session.execute(count_stmt)).scalar() or 0
            stmt = stmt.order_by(PoliceAgent.id.desc()).offset(
                (page - 1) * page_size
            ).limit(page_size)
            result = await session.execute(stmt)
            agents = list(result.scalars().all())
            return agents, total

    async def create(self, data: dict[str, Any]) -> PoliceAgent:
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
            agent = PoliceAgent(**data)
            session.add(agent)
            await session.commit()
            await session.refresh(agent)
            return agent

    async def update(self, agent_id: int, data: dict[str, Any]) -> PoliceAgent | None:
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
            stmt = select(PoliceAgent).where(PoliceAgent.id == agent_id)
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
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
            stmt = select(PoliceAgent).where(PoliceAgent.id == agent_id)
            result = await session.execute(stmt)
            agent = result.scalar_one_or_none()
            if not agent:
                return False
            await session.delete(agent)
            await session.commit()
            return True

    async def update_work_stats(self, agent_id: int, stats: dict[str, Any]) -> bool:
        """更新数字警员工作统计"""
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
            stmt = select(PoliceAgent).where(PoliceAgent.id == agent_id)
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
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
            stmt = select(PoliceAgent).where(PoliceAgent.id == agent_id)
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
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
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
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
            run = PoliceAgentRun(**data)
            session.add(run)
            await session.commit()
            await session.refresh(run)
            return run

    async def update_run(self, run_id: int, data: dict[str, Any]) -> PoliceAgentRun | None:
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
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
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
            stmt = select(PoliceSOP)
            if agent_type:
                stmt = stmt.where(PoliceSOP.agent_type == agent_type)
            if category:
                stmt = stmt.where(PoliceSOP.category == category)
            stmt = stmt.order_by(PoliceSOP.id.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_sop(self, sop_id: int) -> PoliceSOP | None:
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
            stmt = select(PoliceSOP).where(PoliceSOP.id == sop_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create_sop(self, data: dict[str, Any]) -> PoliceSOP:
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
            sop = PoliceSOP(**data)
            session.add(sop)
            await session.commit()
            await session.refresh(sop)
            return sop

    async def update_sop(self, sop_id: int, data: dict[str, Any]) -> PoliceSOP | None:
        from yuxi.storage.postgres.pg_manager import get_async_session_context

        async with get_async_session_context() as session:
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


agent_repository = AgentRepository()
