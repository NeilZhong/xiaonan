"""★ 协助伙伴（子智能体）服务 — CRUD + 数字警员装备区 + 用户连接

复用 Yuxi 现成 subagent 机制，不新造运行时：
- 协助伙伴 = agents 表中 is_subagent=true 的一级 Agent（backend_id=SubAgentBackend），
  由数字警员挂载到 config_json.context.subagents（slug 列表），运行时委派
  （task / subagent_start 等工具）由 Yuxi 中间件 + SubagentRunService 处理。
- 本服务只做「装备区」的数据层与权限层。

权限边界（与数字警员对称，二元收口）：
- 编辑/删除：仅 created_by=current_user 或超管（复用 user_can_manage_agent）。
- 装备/卸载：仅该数字警员的 created_by 或超管。
- 可见性：复用 user_can_access_agent（share_config + approval_status 体系）。
"""

from typing import Any

from sqlalchemy import select

from yuxi.repositories.agent_repository import (
    SUB_AGENT_BACKEND_ID,
    user_can_access_agent,
    user_can_manage_agent,
)
from yuxi.repositories.police_agent_repository import police_agent_repository
from yuxi.services.police_service import write_audit_log
from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_business import Agent, User
from yuxi.storage.postgres.models_police import PoliceAgentConnection
from yuxi.utils import logger


def _read_subagents(agent: Agent) -> list[str]:
    """读取数字警员已装备的协助伙伴 slug 列表（config_json.context.subagents）。"""
    config = agent.config_json or {}
    context = config.get("context") or {}
    return list(context.get("subagents") or [])


def _write_subagents(agent: Agent, slugs: list[str]) -> None:
    """写回数字警员已装备的协助伙伴 slug 列表。"""
    config = dict(agent.config_json or {})
    context = dict(config.get("context") or {})
    context["subagents"] = slugs
    config["context"] = context
    agent.config_json = config


def _partner_to_dict(agent: Agent) -> dict[str, Any]:
    """协助伙伴序列化（不含运行时统计，保持轻量）。"""
    d = agent.to_dict()
    d["is_partner"] = True
    return d


class PolicePartnerService:
    """协助伙伴（子智能体）管理 + 数字警员装备区 + 用户连接"""

    # ── 协助伙伴 CRUD ─────────────────────────────────────

    async def list_partners(
        self, *, current_user: User, keyword: str | None = None,
        category: str | None = None, status: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict[str, Any]:
        """列出当前用户可见的协助伙伴（is_subagent=true）。

        status: mine=我创建的；其余返回全部可见。
        """
        async with pg_manager.get_async_session_context() as session:
            stmt = select(Agent).where(Agent.is_subagent.is_(True))
            if keyword:
                stmt = stmt.where(Agent.name.ilike(f"%{keyword}%"))
            if category:
                stmt = stmt.where(Agent.category == category)
            stmt = stmt.order_by(Agent.id.desc())
            result = await session.execute(stmt)
            all_partners = list(result.scalars().all())
        visible = [a for a in all_partners if user_can_access_agent(current_user, a)]
        if status == "mine":
            visible = [a for a in visible if a.created_by == str(current_user.uid)]
        total = len(visible)
        start = (page - 1) * page_size
        items = [_partner_to_dict(a) for a in visible[start:start + page_size]]
        return {"items": items, "total": total}

    async def get_partner(self, partner_id: int) -> dict[str, Any] | None:
        agent = await police_agent_repository.get_by_id(partner_id)
        if not agent or not agent.is_subagent:
            return None
        return _partner_to_dict(agent)

    async def create_partner(self, *, data: dict[str, Any], current_user: User) -> dict[str, Any]:
        """创建协助伙伴（强制 is_subagent=true + SubAgentBackend）。"""
        payload = {
            "name": (data.get("name") or "").strip(),
            "description": data.get("description"),
            "category": data.get("category"),
            "icon": data.get("icon"),
            "system_prompt": data.get("system_prompt"),
            "model_config": data.get("model_settings") or data.get("model_config"),
            "tools": data.get("tools") or [],
            "skills": data.get("skills") or [],
            "knowledge_base_ids": data.get("knowledge_base_ids") or [],
            "sop_ids": data.get("sop_ids") or [],
            "is_subagent": True,
            "backend_id": SUB_AGENT_BACKEND_ID,
            "share_config": {
                "access_level": "user",
                "department_ids": [],
                "user_uids": [str(current_user.uid)],
            },
            "created_by": str(current_user.uid),
            "agent_type": "subagent",
        }
        agent = await police_agent_repository.create(payload)
        await write_audit_log(
            action="partner.create",
            resource_type="agent",
            resource_id=agent.id,
            user_id=current_user.id,
            user_name=getattr(current_user, "name", None),
            details={"name": agent.name},
        )
        return _partner_to_dict(agent)

    async def update_partner(
        self, *, partner_id: int, data: dict[str, Any], current_user: User,
    ) -> dict[str, Any] | None:
        """编辑协助伙伴。权限：仅创建者或超管。"""
        agent = await police_agent_repository.get_by_id(partner_id)
        if not agent or not agent.is_subagent:
            return None
        if not user_can_manage_agent(current_user, agent):
            raise PermissionError("无权编辑他人创建的协助伙伴")
        payload = {
            k: v for k, v in {
                "name": data.get("name"),
                "description": data.get("description"),
                "category": data.get("category"),
                "icon": data.get("icon"),
                "system_prompt": data.get("system_prompt"),
                "model_config": data.get("model_settings") or data.get("model_config"),
                "tools": data.get("tools"),
                "skills": data.get("skills"),
                "knowledge_base_ids": data.get("knowledge_base_ids"),
                "sop_ids": data.get("sop_ids"),
            }.items() if v is not None
        }
        if not payload:
            return _partner_to_dict(agent)
        updated = await police_agent_repository.update(agent.id, payload)
        await write_audit_log(
            action="partner.update",
            resource_type="agent",
            resource_id=agent.id,
            user_id=current_user.id,
            user_name=getattr(current_user, "name", None),
            details={"name": agent.name},
        )
        return _partner_to_dict(updated)

    async def delete_partner(self, *, partner_id: int, current_user: User) -> bool:
        """删除协助伙伴。权限：仅创建者或超管；先检查被数字警员挂载。"""
        agent = await police_agent_repository.get_by_id(partner_id)
        if not agent or not agent.is_subagent:
            return False
        if not user_can_manage_agent(current_user, agent):
            raise PermissionError("无权删除他人创建的协助伙伴")
        mount_count = await self.count_mounted_by(agent.slug)
        if mount_count > 0:
            raise ValueError(f"仍有 {mount_count} 个数字警员挂载该协助伙伴，请先卸载")
        ok = await police_agent_repository.delete(agent.id)
        if ok:
            await write_audit_log(
                action="partner.delete",
                resource_type="agent",
                resource_id=agent.id,
                user_id=current_user.id,
                user_name=getattr(current_user, "name", None),
                details={"name": agent.name, "slug": agent.slug},
            )
        return ok

    async def count_mounted_by(self, partner_slug: str) -> int:
        """统计有多少数字警员（非子智能体）的 subagents 列表包含该协助伙伴 slug。"""
        async with pg_manager.get_async_session_context() as session:
            stmt = select(Agent).where(Agent.is_subagent.is_(False))
            result = await session.execute(stmt)
            agents = list(result.scalars().all())
        return sum(1 for a in agents if partner_slug in _read_subagents(a))

    async def share_partner(
        self, *, partner_id: int, scope: str, author_id: int | None = None,
        department_ids: list[int] | None = None, user_uids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """设置协助伙伴共享范围（与数字警员 share_agent 同语义，但不授警号）。"""
        agent = await police_agent_repository.get_by_id(partner_id)
        if not agent or not agent.is_subagent:
            return None
        if scope not in ("personal", "department", "user", "global"):
            raise ValueError("无效的共享范围")
        if scope == "global":
            agent.share_config = {"access_level": "global", "department_ids": [], "user_uids": []}
            agent.approval_status = "pending"
        elif scope == "department":
            agent.share_config = {
                "access_level": "department",
                "department_ids": department_ids or [],
                "user_uids": [],
            }
        elif scope == "user":
            agent.share_config = {
                "access_level": "user",
                "department_ids": [],
                "user_uids": user_uids or [],
            }
        else:  # personal
            agent.share_config = {
                "access_level": "user",
                "department_ids": [],
                "user_uids": [str(author_id)] if author_id else [str(agent.created_by)],
            }
        await police_agent_repository.update(agent.id, {
            "share_config": agent.share_config,
            "approval_status": agent.approval_status,
        })
        return _partner_to_dict(agent)

    async def approve_partner(self, *, partner_id: int, approved: bool, reviewer_id: int) -> dict[str, Any] | None:
        """超管审批协助伙伴全局共享申请（不授警号）。"""
        agent = await police_agent_repository.get_by_id(partner_id)
        if not agent or not agent.is_subagent:
            return None
        if agent.approval_status != "pending":
            return None
        agent.approval_status = "approved" if approved else "rejected"
        await police_agent_repository.update(agent.id, {
            "approval_status": agent.approval_status,
        })
        return _partner_to_dict(agent)

    # ── 数字警员装备区 ─────────────────────────────────────

    async def list_equipped(self, *, agent_id: int) -> dict[str, Any]:
        """返回数字警员已装备的协助伙伴（由 subagents slug 展开）。"""
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            return {"items": [], "total": 0}
        slugs = _read_subagents(agent)
        items: list[dict[str, Any]] = []
        for slug in slugs:
            partner = await police_agent_repository.get_by_slug(slug)
            if partner and partner.is_subagent:
                d = _partner_to_dict(partner)
                items.append(d)
        return {"items": items, "total": len(items)}

    async def list_available(self, *, agent_id: int, current_user: User) -> dict[str, Any]:
        """返回当前用户空间可装备但未装备的协助伙伴候选（天赋资产）。"""
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            return {"items": [], "total": 0}
        equipped = set(_read_subagents(agent))
        async with pg_manager.get_async_session_context() as session:
            stmt = select(Agent).where(Agent.is_subagent.is_(True)).order_by(Agent.id.desc())
            result = await session.execute(stmt)
            all_partners = list(result.scalars().all())
        candidates = [
            a for a in all_partners
            if a.slug not in equipped and user_can_access_agent(current_user, a)
        ]
        return {"items": [_partner_to_dict(a) for a in candidates], "total": len(candidates)}

    async def equip_partner(self, *, agent_id: int, partner_id: int, current_user: User) -> dict[str, Any]:
        """给数字警员装备协助伙伴。权限：仅该警员的创建者或超管。"""
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            raise ValueError("数字警员不存在")
        if not user_can_manage_agent(current_user, agent):
            raise PermissionError("无权装备他人创建的数字警员")
        partner = await police_agent_repository.get_by_id(partner_id)
        if not partner or not partner.is_subagent:
            raise ValueError("协助伙伴不存在")
        slugs = _read_subagents(agent)
        if partner.slug not in slugs:
            slugs.append(partner.slug)
            _write_subagents(agent, slugs)
            await police_agent_repository.update(agent.id, {"config_json": agent.config_json})
        await write_audit_log(
            action="partner.equip",
            resource_type="agent",
            resource_id=agent.id,
            user_id=current_user.id,
            user_name=getattr(current_user, "name", None),
            details={"partner_slug": partner.slug},
        )
        return await self.list_equipped(agent_id=agent.id)

    async def unequip_partner(self, *, agent_id: int, partner_id: int, current_user: User) -> dict[str, Any]:
        """从数字警员卸载协助伙伴。权限：仅该警员的创建者或超管。"""
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            raise ValueError("数字警员不存在")
        if not user_can_manage_agent(current_user, agent):
            raise PermissionError("无权卸载他人创建的数字警员")
        partner = await police_agent_repository.get_by_id(partner_id)
        if not partner:
            raise ValueError("协助伙伴不存在")
        slugs = _read_subagents(agent)
        if partner.slug in slugs:
            slugs.remove(partner.slug)
            _write_subagents(agent, slugs)
            await police_agent_repository.update(agent.id, {"config_json": agent.config_json})
        await write_audit_log(
            action="partner.unequip",
            resource_type="agent",
            resource_id=agent.id,
            user_id=current_user.id,
            user_name=getattr(current_user, "name", None),
            details={"partner_slug": partner.slug},
        )
        return await self.list_equipped(agent_id=agent.id)

    # ── 用户 ↔ 数字警员连接 ────────────────────────────────

    async def apply_connection(self, *, agent_id: int, current_user: User) -> dict[str, Any]:
        """用户申请连接某数字警员（市场「申请使用」）。

        可见即连接：department/user 共享直接 active；global 需先经超管审批，
        但 agent 能出现在用户可见列表即已过 approval_status，故此处直接 active。
        """
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent or agent.is_subagent:
            raise ValueError("数字警员不存在")
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentConnection).where(
                PoliceAgentConnection.user_id == current_user.id,
                PoliceAgentConnection.agent_id == agent_id,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                return existing.to_dict()
            conn = PoliceAgentConnection(
                user_id=current_user.id,
                agent_id=agent_id,
                status="active",
                approved_at=None,
            )
            session.add(conn)
            await session.commit()
            await session.refresh(conn)
        await write_audit_log(
            action="connection.apply",
            resource_type="agent",
            resource_id=agent_id,
            user_id=current_user.id,
            user_name=getattr(current_user, "name", None),
            details={"agent_slug": agent.slug},
        )
        return conn.to_dict()

    async def list_connections(
        self, *, current_user: User, status: str | None = None,
    ) -> dict[str, Any]:
        """当前用户的数字警员连接列表（含警员摘要）。"""
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceAgentConnection).where(
                PoliceAgentConnection.user_id == current_user.id
            )
            if status:
                stmt = stmt.where(PoliceAgentConnection.status == status)
            stmt = stmt.order_by(PoliceAgentConnection.id.desc())
            result = await session.execute(stmt)
            conns = list(result.scalars().all())
        items = []
        for conn in conns:
            d = conn.to_dict()
            agent = await police_agent_repository.get_by_id(conn.agent_id)
            d["agent"] = agent.to_dict() if agent else None
            items.append(d)
        return {"items": items, "total": len(items)}

    async def delete_connection(self, *, connection_id: int, current_user: User) -> bool:
        """解除连接（不影响数字警员本身）。仅本人或超管。"""
        async with pg_manager.get_async_session_context() as session:
            conn = await session.get(PoliceAgentConnection, connection_id)
            if not conn:
                return False
            if conn.user_id != current_user.id and current_user.role not in ("admin", "superadmin"):
                raise PermissionError("无权解除该连接")
            await session.delete(conn)
            await session.commit()
        return True


police_partner_service = PolicePartnerService()
