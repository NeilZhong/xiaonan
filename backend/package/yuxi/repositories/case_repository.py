"""★ 案件数据访问层"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_police import CaseMember, CasePhase, PoliceCase


class CaseRepository:
    """案件数据访问层 — 自管理 Session 模式"""

    async def get_by_id(self, case_id: int) -> PoliceCase | None:
        async with pg_manager.get_async_session_context() as session:
            return await self.get_by_id_with_db(session, case_id)

    async def get_by_id_with_db(self, db: AsyncSession, case_id: int) -> PoliceCase | None:
        result = await db.execute(select(PoliceCase).where(PoliceCase.id == case_id))
        return result.scalar_one_or_none()

    async def list_cases(
        self,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        phase: str | None = None,
        case_type: str | None = None,
        keyword: str | None = None,
        user_id: int | None = None,
    ) -> tuple[list[PoliceCase], int]:
        """列表查询 + 总数，支持筛选和关键词搜索"""
        async with pg_manager.get_async_session_context() as session:
            query = select(PoliceCase)
            count_query = select(func.count(PoliceCase.id))

            if status:
                query = query.where(PoliceCase.status == status)
                count_query = count_query.where(PoliceCase.status == status)
            if phase:
                query = query.where(PoliceCase.phase == phase)
                count_query = count_query.where(PoliceCase.phase == phase)
            if case_type:
                query = query.where(PoliceCase.case_type == case_type)
                count_query = count_query.where(PoliceCase.case_type == case_type)
            if keyword:
                pattern = f"%{keyword}%"
                query = query.where(PoliceCase.title.ilike(pattern) | PoliceCase.case_number.ilike(pattern))
                count_query = count_query.where(
                    PoliceCase.title.ilike(pattern) | PoliceCase.case_number.ilike(pattern)
                )
            if user_id:
                # 仅返回用户参与的案件
                member_subq = select(CaseMember.case_id).where(CaseMember.user_id == user_id)
                query = query.where(PoliceCase.id.in_(member_subq))
                count_query = count_query.where(PoliceCase.id.in_(member_subq))

            query = query.order_by(PoliceCase.created_at.desc()).offset(skip).limit(limit)
            result = await session.execute(query)
            cases = list(result.scalars().all())
            count_result = await session.execute(count_query)
            total = count_result.scalar() or 0
            return cases, total

    async def create(self, data: dict[str, Any]) -> PoliceCase:
        async with pg_manager.get_async_session_context() as session:
            case = PoliceCase(**data)
            session.add(case)
            await session.commit()
            await session.refresh(case)
            return case

    async def update(self, case_id: int, data: dict[str, Any]) -> PoliceCase | None:
        async with pg_manager.get_async_session_context() as session:
            case = await session.get(PoliceCase, case_id)
            if not case:
                return None
            for key, value in data.items():
                if hasattr(case, key) and value is not None:
                    setattr(case, key, value)
            await session.commit()
            await session.refresh(case)
            return case

    async def delete(self, case_id: int) -> bool:
        async with pg_manager.get_async_session_context() as session:
            case = await session.get(PoliceCase, case_id)
            if not case:
                return False
            await session.delete(case)
            await session.commit()
            return True

    # ── 案件成员 ──────────────────────────────────────────────

    async def add_member(self, case_id: int, user_id: int, role: str) -> CaseMember:
        async with pg_manager.get_async_session_context() as session:
            member = CaseMember(case_id=case_id, user_id=user_id, role=role)
            session.add(member)
            await session.commit()
            await session.refresh(member)
            return member

    async def list_members(self, case_id: int) -> list[CaseMember]:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(CaseMember).where(CaseMember.case_id == case_id).order_by(CaseMember.joined_at)
            )
            return list(result.scalars().all())

    async def remove_member(self, case_id: int, user_id: int) -> bool:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(CaseMember).where(CaseMember.case_id == case_id, CaseMember.user_id == user_id)
            )
            member = result.scalar_one_or_none()
            if not member:
                return False
            await session.delete(member)
            await session.commit()
            return True

    # ── 案件阶段 ──────────────────────────────────────────────

    async def list_phases(self, case_id: int) -> list[CasePhase]:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(CasePhase).where(CasePhase.case_id == case_id).order_by(CasePhase.started_at)
            )
            return list(result.scalars().all())

    async def update_phase(self, case_id: int, phase: str) -> PoliceCase | None:
        async with pg_manager.get_async_session_context() as session:
            case = await session.get(PoliceCase, case_id)
            if not case:
                return None
            old_phase = case.phase
            case.phase = phase
            # 记录新阶段
            phase_record = CasePhase(case_id=case_id, phase=phase, status="active")
            session.add(phase_record)
            # 结束旧阶段
            if old_phase:
                from yuxi.utils.datetime_utils import utc_now_naive

                result = await session.execute(
                    select(CasePhase)
                    .where(CasePhase.case_id == case_id, CasePhase.phase == old_phase, CasePhase.status == "active")
                )
                old_phase_record = result.scalar_one_or_none()
                if old_phase_record:
                    old_phase_record.status = "completed"
                    old_phase_record.completed_at = utc_now_naive()
            await session.commit()
            await session.refresh(case)
            return case


case_repository = CaseRepository()
