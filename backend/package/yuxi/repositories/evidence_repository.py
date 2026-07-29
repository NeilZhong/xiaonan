"""★ 证据材料数据访问层"""

import hashlib
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_police import Evidence, EvidenceLink
from yuxi.utils.datetime_utils import utc_now_naive


class EvidenceRepository:
    """证据材料数据访问层"""

    async def get_by_id(self, evidence_id: int) -> Evidence | None:
        async with pg_manager.get_async_session_context() as session:
            return await session.get(Evidence, evidence_id)

    async def list_evidence(
        self,
        case_id: int,
        skip: int = 0,
        limit: int = 50,
        evidence_type: str | None = None,
        task_id: int | None = None,
    ) -> tuple[list[Evidence], int]:
        async with pg_manager.get_async_session_context() as session:
            query = select(Evidence).where(Evidence.case_id == case_id)
            count_query = select(func.count(Evidence.id)).where(Evidence.case_id == case_id)

            if evidence_type:
                query = query.where(Evidence.type == evidence_type)
                count_query = count_query.where(Evidence.type == evidence_type)
            if task_id:
                query = query.where(Evidence.task_id == task_id)
                count_query = count_query.where(Evidence.task_id == task_id)

            query = query.order_by(Evidence.created_at.desc()).offset(skip).limit(limit)
            result = await session.execute(query)
            items = list(result.scalars().all())
            count_result = await session.execute(count_query)
            total = count_result.scalar() or 0
            return items, total

    async def create(self, data: dict[str, Any]) -> Evidence:
        async with pg_manager.get_async_session_context() as session:
            evidence = Evidence(**data)
            session.add(evidence)
            await session.commit()
            await session.refresh(evidence)
            return evidence

    async def update(self, evidence_id: int, data: dict[str, Any]) -> Evidence | None:
        async with pg_manager.get_async_session_context() as session:
            evidence = await session.get(Evidence, evidence_id)
            if not evidence:
                return None
            for key, value in data.items():
                if hasattr(evidence, key) and value is not None:
                    setattr(evidence, key, value)
            await session.commit()
            await session.refresh(evidence)
            return evidence

    async def review(
        self, evidence_id: int, reviewer_id: int, reviewer_police_id: str, file_hash: str | None = None
    ) -> Evidence | None:
        """审核证据材料 — 计算 signed_hash (POLICE_REQUIREMENTS §9.5)"""
        async with pg_manager.get_async_session_context() as session:
            evidence = await session.get(Evidence, evidence_id)
            if not evidence:
                return None
            reviewed_at = utc_now_naive()
            # signed_hash = SHA-256(民警警号 + 审核时间戳ISO + file_hash)
            hash_input = f"{reviewer_police_id}{reviewed_at.isoformat()}{file_hash or evidence.file_hash or ''}"
            signed_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            evidence.reviewed_by = reviewer_id
            evidence.reviewed_at = reviewed_at
            evidence.signed_hash = signed_hash
            await session.commit()
            await session.refresh(evidence)
            return evidence

    async def list_links(self, case_id: int) -> list[EvidenceLink]:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(EvidenceLink).where(EvidenceLink.case_id == case_id).order_by(EvidenceLink.created_at)
            )
            return list(result.scalars().all())

    async def create_link(self, data: dict[str, Any]) -> EvidenceLink:
        async with pg_manager.get_async_session_context() as session:
            link = EvidenceLink(**data)
            session.add(link)
            await session.commit()
            await session.refresh(link)
            return link


evidence_repository = EvidenceRepository()
