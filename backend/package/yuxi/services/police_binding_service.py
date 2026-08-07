"""★ 授权绑定与伙伴关联服务（P2c）

- 用户「添加」数字警员 = 建立与共享实例的连接（police_agent_connections），**不复制**；
  若被添加的警员已关联协助伙伴，则**级联**把这些（已上架的）伙伴一并加入用户空间。
- 绑定支持版本 pin（钉住/跟随最新）、昵称与通知偏好；绑定不影响源智能体定义。
- 数字警察 ↔ 协助伙伴 的关联（agent_associated_partners）由创建者在「关联伙伴」界面设置。

模块级单例：agent_binding_service
"""

from typing import Any

from sqlalchemy import select

from yuxi.repositories.agent_repository import ADMIN_ROLES, user_can_manage_agent
from yuxi.repositories.police_agent_repository import police_agent_repository
from yuxi.repositories.police_binding_repository import (
    agent_associated_partner_repository,
    agent_binding_repository,
)
from yuxi.services.police_service import write_audit_log
from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_business import Agent
from yuxi.storage.postgres.models_police import PoliceAgentVersion
from yuxi.utils import logger


def _agent_summary(agent: Agent) -> dict[str, Any]:
    return {
        "id": agent.id,
        "slug": agent.slug,
        "name": agent.name,
        "icon": getattr(agent, "icon", None),
        "agent_type": getattr(agent, "agent_type", None),
        "is_subagent": bool(getattr(agent, "is_subagent", False)),
        "status": agent.status,
        "department": getattr(agent, "department", None),
    }


class AgentBindingService:
    """授权绑定与伙伴关联服务"""

    # ── 添加（市场「申请使用」/「我的数字警员」）──────────────────

    async def apply(self, *, agent_id: int, current_user: Any) -> dict[str, Any]:
        """用户申请连接某数字警员，并级联添加其已上架的关联协助伙伴。

        幂等：已存在连接则复用。级联伙伴连接同样幂等（已存在跳过）。
        """
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent or agent.is_subagent:
            raise ValueError("数字警员不存在")
        conn, _created = await agent_binding_repository.ensure_connection(
            user_id=current_user.id, agent_id=agent_id, status="active",
        )
        cascaded_partner_ids = await self._cascade_partners(
            agent_id=agent_id, user_id=current_user.id,
        )
        await write_audit_log(
            action="connection.apply",
            resource_type="agent",
            resource_id=agent_id,
            user_id=current_user.id,
            user_name=getattr(current_user, "name", None),
            details={"agent_slug": agent.slug, "cascaded_partner_ids": cascaded_partner_ids},
        )
        result = conn.to_dict()
        result["agent"] = _agent_summary(agent)
        result["cascaded_partner_ids"] = cascaded_partner_ids
        return result

    async def _cascade_partners(self, *, agent_id: int, user_id: int) -> list[int]:
        """读取该警员关联（已上架）的伙伴并幂等建立用户连接；返回实际新增的伙伴 id。"""
        partner_ids = await agent_associated_partner_repository.list_partner_ids(agent_id)
        added: list[int] = []
        for pid in partner_ids:
            partner = await police_agent_repository.get_by_id(pid)
            # 仅级联「已上架」协助伙伴（approval_status 为空=历史/内置，approved=已审）
            if not partner or not partner.is_subagent:
                continue
            if (partner.approval_status or "approved") not in (None, "approved"):
                continue
            _conn, created = await agent_binding_repository.ensure_connection(
                user_id=user_id, agent_id=pid, status="active",
            )
            if created:
                added.append(pid)
        return added

    # ── 版本 pin / 偏好 ────────────────────────────────────────

    async def pin(self, *, connection_id: int, version_id: int, current_user: Any) -> dict[str, Any]:
        conn = await agent_binding_repository.get(connection_id)
        if not conn:
            raise ValueError("连接不存在")
        if conn.user_id != current_user.id and current_user.role not in ADMIN_ROLES:
            raise PermissionError("无权操作该绑定")
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentVersion).where(PoliceAgentVersion.id == version_id)
            version = (await session.execute(stmt)).scalar_one_or_none()
        if not version or version.agent_id != conn.agent_id:
            raise ValueError("版本不存在或不属于该智能体")
        await agent_binding_repository.set_pinned_version(connection_id, version_id)
        return (await agent_binding_repository.get(connection_id)).to_dict()

    async def unpin(self, *, connection_id: int, current_user: Any) -> dict[str, Any]:
        conn = await agent_binding_repository.get(connection_id)
        if not conn:
            raise ValueError("连接不存在")
        if conn.user_id != current_user.id and current_user.role not in ADMIN_ROLES:
            raise PermissionError("无权操作该绑定")
        await agent_binding_repository.set_pinned_version(connection_id, None)
        return (await agent_binding_repository.get(connection_id)).to_dict()

    async def set_prefs(
        self, *, connection_id: int, current_user: Any,
        nickname: str | None = None, notify_new_version: bool | None = None,
    ) -> dict[str, Any]:
        conn = await agent_binding_repository.get(connection_id)
        if not conn:
            raise ValueError("连接不存在")
        if conn.user_id != current_user.id and current_user.role not in ADMIN_ROLES:
            raise PermissionError("无权操作该绑定")
        await agent_binding_repository.set_prefs(
            connection_id, nickname=nickname, notify_new_version=notify_new_version,
        )
        return (await agent_binding_repository.get(connection_id)).to_dict()

    async def remove(self, *, connection_id: int, current_user: Any) -> None:
        conn = await agent_binding_repository.get(connection_id)
        if not conn:
            raise ValueError("连接不存在")
        if conn.user_id != current_user.id and current_user.role not in ADMIN_ROLES:
            raise PermissionError("无权操作该绑定")
        # 仅移除用户绑定；级联添加的伙伴连接独立生命周期，保留不删（添加时快照语义）
        await agent_binding_repository.remove(connection_id)

    # ── 列表 / 详情 ─────────────────────────────────────────────

    async def list_mine(self, *, current_user: Any) -> dict[str, Any]:
        """当前用户全部绑定，含源智能体摘要、钉住的版本、以及该智能体关联的伙伴列表。"""
        rows = await agent_binding_repository.list_by_user(user_id=current_user.id)
        items: list[dict[str, Any]] = []
        # 批量预取伙伴摘要，避免 N+1
        partner_id_batches: set[int] = set()
        for _conn, agent in rows:
            pids = await agent_associated_partner_repository.list_partner_ids(agent.id)
            partner_id_batches.update(pids)
        partner_summary: dict[int, dict[str, Any]] = {}
        if partner_id_batches:
            async with pg_manager.get_async_session_context() as session:
                stmt = select(Agent).where(Agent.id.in_(list(partner_id_batches)))
                for ag in (await session.execute(stmt)).scalars().all():
                    partner_summary[ag.id] = _agent_summary(ag)

        for conn, agent in rows:
            item = conn.to_dict()
            item["agent"] = _agent_summary(agent)
            # 钉住的版本摘要
            if conn.pinned_version_id:
                async with pg_manager.get_async_session_context() as session:
                    vstmt = select(PoliceAgentVersion).where(PoliceAgentVersion.id == conn.pinned_version_id)
                    ver = (await session.execute(vstmt)).scalar_one_or_none()
                item["pinned_version"] = (
                    {"id": ver.id, "version_label": ver.version_label, "status": ver.status,
                     "release_mode": ver.release_mode}
                    if ver else None
                )
            # 该智能体关联的伙伴
            pids = await agent_associated_partner_repository.list_partner_ids(agent.id)
            item["associated_partners"] = [partner_summary.get(pid) for pid in pids if pid in partner_summary]
            items.append(item)
        return {"items": items, "total": len(items)}

    # ── 数字警察 ↔ 协助伙伴 关联（创建者侧）────────────────────

    async def set_partners(
        self, *, agent_id: int, partner_ids: list[int], current_user: Any,
    ) -> dict[str, Any]:
        """设置某数字警员的关联协助伙伴（全量替换）。仅创建者/管理员可操作。"""
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent or agent.is_subagent:
            raise ValueError("数字警员不存在")
        if not user_can_manage_agent(current_user, agent):
            raise PermissionError("仅创建者或管理员可设置关联伙伴")
        # 校验每个 partner 合法（确为协助伙伴、已上架）
        valid_ids: list[int] = []
        for pid in partner_ids:
            partner = await police_agent_repository.get_by_id(pid)
            if not partner or not partner.is_subagent:
                continue
            if (partner.approval_status or "approved") not in (None, "approved"):
                continue
            valid_ids.append(pid)
        created = await agent_associated_partner_repository.set_partners(
            digital_police_id=agent_id, partner_ids=valid_ids,
        )
        await write_audit_log(
            action="agent.associate_partners",
            resource_type="agent",
            resource_id=agent_id,
            user_id=current_user.id,
            user_name=getattr(current_user, "name", None),
            details={"partner_ids": valid_ids},
        )
        return {"digital_police_id": agent_id, "partner_ids": valid_ids, "count": len(created)}

    async def list_partners(self, *, agent_id: int, current_user: Any) -> dict[str, Any]:
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent or agent.is_subagent:
            raise ValueError("数字警员不存在")
        if not user_can_manage_agent(current_user, agent):
            raise PermissionError("仅创建者或管理员可查看关联伙伴")
        rows = await agent_associated_partner_repository.list_associations(agent_id)
        partners = [_agent_summary(ag) for _assoc, ag in rows]
        return {"digital_police_id": agent_id, "partners": partners, "total": len(partners)}


agent_binding_service = AgentBindingService()
