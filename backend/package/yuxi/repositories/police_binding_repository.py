"""★ 授权绑定与伙伴关联仓储（P2c）

- AgentBindingRepository：用户 ↔ 数字警员/协助伙伴 连接（police_agent_connections）
  的 CRUD、版本 pin、偏好、级联幂等插入、可见性集合查询。
- AgentAssociatedPartnerRepository：数字警察 ↔ 协助伙伴 定义侧关联（agent_associated_partners）
  的全量替换与查询。

遵循 police_* 仓储约定：无 __init__、自持 session（pg_manager 上下文）、模块级单例。
"""

from typing import Any

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_business import Agent
from yuxi.storage.postgres.models_police import (
    AgentAssociatedPartner,
    PoliceAgentConnection,
)
from yuxi.utils.datetime_utils import utc_now_naive
from yuxi.utils import logger


class AgentBindingRepository:
    """用户 ↔ 智能体 连接仓储（绑定表 police_agent_connections）"""

    async def get(self, connection_id: int) -> PoliceAgentConnection | None:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentConnection).where(PoliceAgentConnection.id == connection_id)
            return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_user_agent(self, user_id: int, agent_id: int) -> PoliceAgentConnection | None:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentConnection).where(
                PoliceAgentConnection.user_id == user_id,
                PoliceAgentConnection.agent_id == agent_id,
            )
            return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_user(
        self, *, user_id: int, status: str | None = None,
    ) -> list[tuple[PoliceAgentConnection, Agent]]:
        """当前用户全部连接（联表返回 (connection, agent) 元组，供 service 组装摘要）。"""
        async with pg_manager.get_async_session_context() as session:
            stmt = (
                select(PoliceAgentConnection, Agent)
                .join(Agent, Agent.id == PoliceAgentConnection.agent_id)
                .where(PoliceAgentConnection.user_id == user_id)
            )
            if status:
                stmt = stmt.where(PoliceAgentConnection.status == status)
            stmt = stmt.order_by(PoliceAgentConnection.id.desc())
            return list((await session.execute(stmt)).all())

    async def list_connected_agent_ids(self, user_id: int) -> set[int]:
        """当前用户 active 连接覆盖的 agent_id 集合（供 list_agents 可见性批量判断，避免 N+1）。"""
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentConnection.agent_id).where(
                PoliceAgentConnection.user_id == user_id,
                PoliceAgentConnection.status == "active",
            )
            return {row[0] for row in (await session.execute(stmt)).all()}

    async def count_active_by_agent(self) -> dict[int, int]:
        """全平台各智能体的 active 绑定数（治理后台状态总览用，单次聚合避免 N+1）。"""
        async with pg_manager.get_async_session_context() as session:
            stmt = (
                select(PoliceAgentConnection.agent_id, func.count(PoliceAgentConnection.id))
                .where(PoliceAgentConnection.status == "active")
                .group_by(PoliceAgentConnection.agent_id)
            )
            return {row[0]: row[1] for row in (await session.execute(stmt)).all()}

    async def ensure_connection(
        self, *, user_id: int, agent_id: int, status: str = "active",
    ) -> tuple[PoliceAgentConnection, bool]:
        """幂等建立连接：已存在则复用（状态升级 pending→active），否则新建。返回 (conn, created)。"""
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentConnection).where(
                PoliceAgentConnection.user_id == user_id,
                PoliceAgentConnection.agent_id == agent_id,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                if existing.status != "active" and status == "active":
                    existing.status = "active"
                    await session.commit()
                    await session.refresh(existing)
                return existing, False
            conn = PoliceAgentConnection(user_id=user_id, agent_id=agent_id, status=status)
            session.add(conn)
            await session.commit()
            await session.refresh(conn)
            return conn, True

    async def set_pinned_version(self, connection_id: int, version_id: int | None) -> None:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentConnection).where(PoliceAgentConnection.id == connection_id)
            conn = (await session.execute(stmt)).scalar_one_or_none()
            if not conn:
                raise ValueError("连接不存在")
            conn.pinned_version_id = version_id
            conn.pinned_at = utc_now_naive() if version_id is not None else None
            await session.commit()

    async def set_prefs(
        self,
        connection_id: int,
        *,
        nickname: str | None = None,
        notify_new_version: bool | None = None,
    ) -> None:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentConnection).where(PoliceAgentConnection.id == connection_id)
            conn = (await session.execute(stmt)).scalar_one_or_none()
            if not conn:
                raise ValueError("连接不存在")
            if nickname is not None:
                conn.nickname = nickname or None
            if notify_new_version is not None:
                conn.notify_new_version = bool(notify_new_version)
            await session.commit()

    async def remove(self, connection_id: int) -> None:
        async with pg_manager.get_async_session_context() as session:
            await session.execute(
                sa_delete(PoliceAgentConnection).where(PoliceAgentConnection.id == connection_id)
            )
            await session.commit()


class AgentAssociatedPartnerRepository:
    """数字警察 ↔ 协助伙伴 定义侧关联仓储（agent_associated_partners）"""

    async def set_partners(self, *, digital_police_id: int, partner_ids: list[int]) -> list[AgentAssociatedPartner]:
        """全量替换某数字警员的关联伙伴（先删后插，事务内）。"""
        async with pg_manager.get_async_session_context() as session:
            await session.execute(
                sa_delete(AgentAssociatedPartner).where(
                    AgentAssociatedPartner.digital_police_id == digital_police_id
                )
            )
            created: list[AgentAssociatedPartner] = []
            for pid in partner_ids:
                row = AgentAssociatedPartner(digital_police_id=digital_police_id, partner_id=pid)
                session.add(row)
                created.append(row)
            await session.commit()
            for row in created:
                await session.refresh(row)
            return created

    async def list_partner_ids(self, digital_police_id: int) -> list[int]:
        async with pg_manager.get_async_session_context() as session:
            stmt = select(AgentAssociatedPartner.partner_id).where(
                AgentAssociatedPartner.digital_police_id == digital_police_id
            )
            return [row[0] for row in (await session.execute(stmt)).all()]

    async def list_associations(
        self, digital_police_id: int,
    ) -> list[tuple[AgentAssociatedPartner, Agent]]:
        """联表返回 (association, partner_agent) 元组，供 service 组装伙伴摘要。"""
        async with pg_manager.get_async_session_context() as session:
            stmt = (
                select(AgentAssociatedPartner, Agent)
                .join(Agent, Agent.id == AgentAssociatedPartner.partner_id)
                .where(AgentAssociatedPartner.digital_police_id == digital_police_id)
            )
            return list((await session.execute(stmt)).all())


agent_binding_repository = AgentBindingRepository()
agent_associated_partner_repository = AgentAssociatedPartnerRepository()
