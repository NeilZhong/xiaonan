"""★ 案件工作区仓储 — 案件独立存储命名空间 + 树状节点 CRUD

遵循 yuxi 仓储规范：自管理 session（pg_manager.get_async_session_context）。
"""

from typing import Any

from sqlalchemy import delete, select

from yuxi.storage.postgres.models_police import PoliceCaseWorkspace, PoliceWorkspaceNode


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

    # ── 树状节点 ────────────────────────────────────────────────

    async def list_nodes(self, workspace_id: int, parent_id: int | None = None) -> list[PoliceWorkspaceNode]:
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceWorkspaceNode).where(PoliceWorkspaceNode.workspace_id == workspace_id)
            if parent_id is not None:
                stmt = stmt.where(PoliceWorkspaceNode.parent_id == parent_id)
            else:
                stmt = stmt.where(PoliceWorkspaceNode.parent_id.is_(None))
            stmt = stmt.order_by(PoliceWorkspaceNode.node_type.desc(), PoliceWorkspaceNode.name.asc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_nodes_by_workspace(self, workspace_id: int) -> list[PoliceWorkspaceNode]:
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            stmt = (
                select(PoliceWorkspaceNode)
                .where(PoliceWorkspaceNode.workspace_id == workspace_id)
                .order_by(PoliceWorkspaceNode.node_type.desc(), PoliceWorkspaceNode.name.asc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_node(self, node_id: int) -> PoliceWorkspaceNode | None:
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceWorkspaceNode).where(PoliceWorkspaceNode.id == node_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_node_by_name(
        self, workspace_id: int, name: str, parent_id: int | None = None
    ) -> PoliceWorkspaceNode | None:
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            stmt = (
                select(PoliceWorkspaceNode)
                .where(PoliceWorkspaceNode.workspace_id == workspace_id)
                .where(PoliceWorkspaceNode.name == name)
            )
            if parent_id is not None:
                stmt = stmt.where(PoliceWorkspaceNode.parent_id == parent_id)
            else:
                stmt = stmt.where(PoliceWorkspaceNode.parent_id.is_(None))
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create_node(self, data: dict[str, Any]) -> PoliceWorkspaceNode:
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            node = PoliceWorkspaceNode(**data)
            session.add(node)
            await session.commit()
            await session.refresh(node)
            return node

    async def update_node(self, node_id: int, data: dict[str, Any]) -> PoliceWorkspaceNode | None:
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceWorkspaceNode).where(PoliceWorkspaceNode.id == node_id)
            result = await session.execute(stmt)
            node = result.scalar_one_or_none()
            if not node:
                return None
            for k, v in data.items():
                if hasattr(node, k) and v is not None:
                    setattr(node, k, v)
            await session.commit()
            await session.refresh(node)
            return node

    async def delete_node(self, node_id: int) -> bool:
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            stmt = delete(PoliceWorkspaceNode).where(PoliceWorkspaceNode.id == node_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def delete_nodes_by_workspace(self, workspace_id: int) -> None:
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            stmt = delete(PoliceWorkspaceNode).where(PoliceWorkspaceNode.workspace_id == workspace_id)
            await session.execute(stmt)
            await session.commit()


police_workspace_repository = PoliceWorkspaceRepository()
