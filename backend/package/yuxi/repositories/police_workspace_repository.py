"""★ 案件工作区仓储 — 案件独立存储命名空间的 CRUD

遵循 yuxi 仓储规范：自管理 session（pg_manager.get_async_session_context）。
"""

from typing import Any

from sqlalchemy import select

from yuxi.storage.postgres.models_police import PoliceCaseWorkspace


class PoliceWorkspaceRepository:
    """案件工作区仓储"""

    async def get_by_case_id(self, case_id: int) -> PoliceCaseWorkspace | None:
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceCaseWorkspace).where(PoliceCaseWorkspace.case_id == case_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_id(self, workspace_id: int) -> PoliceCaseWorkspace | None:
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceCaseWorkspace).where(PoliceCaseWorkspace.id == workspace_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create(self, data: dict[str, Any]) -> PoliceCaseWorkspace:
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            workspace = PoliceCaseWorkspace(**data)
            session.add(workspace)
            await session.commit()
            await session.refresh(workspace)
            return workspace

    async def update(self, workspace_id: int, data: dict[str, Any]) -> PoliceCaseWorkspace | None:
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceCaseWorkspace).where(PoliceCaseWorkspace.id == workspace_id)
            result = await session.execute(stmt)
            workspace = result.scalar_one_or_none()
            if not workspace:
                return None
            for k, v in data.items():
                if hasattr(workspace, k) and v is not None:
                    setattr(workspace, k, v)
            await session.commit()
            await session.refresh(workspace)
            return workspace

    async def upsert(self, data: dict[str, Any]) -> PoliceCaseWorkspace:
        """按 case_id 幂等写入：存在则更新，不存在则创建"""
        from yuxi.storage.postgres.manager import pg_manager

        case_id = data.get("case_id")
        async with pg_manager.get_async_session_context() as session:
            existing = None
            if case_id is not None:
                stmt = select(PoliceCaseWorkspace).where(PoliceCaseWorkspace.case_id == case_id)
                existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k) and v is not None:
                        setattr(existing, k, v)
                await session.commit()
                await session.refresh(existing)
                return existing
            workspace = PoliceCaseWorkspace(**data)
            session.add(workspace)
            await session.commit()
            await session.refresh(workspace)
            return workspace


police_workspace_repository = PoliceWorkspaceRepository()
