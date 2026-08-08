"""★ 小南市场服务 — 探索浏览 + 发布 / 审核（模块 A）

复用既有能力，不重复造轮子：
- 探索：数字警员（agents 表，非 subagent）→ police_agent_repository.list_agents（含可见性过滤）
        协助伙伴（is_subagent=true）→ police_partner_service.list_partners
        任务模板 → police_task_template_service.list_templates
- 申请使用（apply_mode）：
        数字警员 → connect（写 police_agent_connections，建立连接不复制身份）
        协助伙伴 → equip_guided（引导去数字警员档案页装备，不直接挂载）
        模板 → install（MVP 仅确认，不复制）
- 发布 / 审核：
        数字警员 → police_agent_service.share_agent(scope=global → pending) / approve_agent
        协助伙伴 → police_partner_service.share_partner / approve_partner
        模板 → MVP 直接 enabled 上架（模板表无审批链）

MVP 范围（v2.1 R-02）：发布仅支持「完整复刻」；「切片打包」为 P2 未来扩展。
"""

from typing import Any

from sqlalchemy import select

from yuxi.repositories.agent_repository import user_can_access_agent, user_can_manage_agent
from yuxi.repositories.police_agent_repository import police_agent_repository
from yuxi.repositories.police_binding_repository import agent_binding_repository
from yuxi.services.police_partner_service import police_partner_service
from yuxi.services.police_service import police_agent_service, write_audit_log
from yuxi.services.police_task_template_service import police_task_template_service
from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_business import Agent, User

# 市场可浏览类型（数字警员 / 协助伙伴 / 任务模板）；技能、工具、MCP、卡片为未来扩展
MARKET_TYPES = ("agent", "partner", "template")


class PoliceMarketService:
    """市场：探索浏览 + 发布/审核。"""

    # ── 探索浏览 ─────────────────────────────────────────

    async def explore(
        self, *, type: str = "all", keyword: str | None = None,
        category: str | None = None, page: int = 1, page_size: int = 50,
        current_user: User,
    ) -> dict[str, Any]:
        """市场探索列表，统一返回结构（前端一张卡片组件可渲染）。

        type: all / agent / partner / template；支持 keyword / category 过滤与分页。
        """
        if type not in ("all", *MARKET_TYPES):
            raise ValueError("不支持的资产类型")

        items: list[dict[str, Any]] = []
        total = 0
        per_type = max(page_size // 2, 20)  # all 时按类型均分，保证各类型都有展示

        if type in ("all", "agent"):
            agents, agent_total = await self._explore_agents(
                keyword=keyword, category=category, page=page, page_size=per_type,
                current_user=current_user,
            )
            items.extend(agents)
            total += agent_total
        if type in ("all", "partner"):
            partners, partner_total = await self._explore_partners(
                keyword=keyword, category=category, page=page, page_size=per_type,
                current_user=current_user,
            )
            items.extend(partners)
            total += partner_total
        if type in ("all", "template"):
            templates = await self._explore_templates(keyword=keyword, category=category)
            items.extend(templates)
            total += len(templates)

        # 统一排序：创建时间倒序（模板无 created_at 时排最后）
        items.sort(key=lambda it: it.get("created_at") or "", reverse=True)
        start = (page - 1) * page_size
        return {"items": items[start:start + page_size], "total": total, "page": page}

    async def _explore_agents(
        self, *, keyword: str | None, category: str | None,
        page: int, page_size: int, current_user: User,
    ) -> tuple[list[dict[str, Any]], int]:
        agents, total = await police_agent_repository.list_agents(
            keyword=keyword, category=category, page=page, page_size=page_size,
            current_user=current_user,
        )
        items = []
        for a in agents:
            d = a.to_dict()
            items.append({
                "id": a.id,
                "type": "agent",
                "name": a.name,
                "description": d.get("description") or a.description or "",
                "category": a.category or "数字民警",
                "author": d.get("badge_number") or "小南官方",
                "avatar": d.get("icon") or "",
                "tags": d.get("capabilities") or [],
                "apply_mode": "connect",
                "stats": {"usage": d.get("install_count") or 0, "rating": 0, "review_count": 0},
                "created_at": d.get("created_at") or "",
            })
        return items, total

    async def _explore_partners(
        self, *, keyword: str | None, category: str | None,
        page: int, page_size: int, current_user: User,
    ) -> tuple[list[dict[str, Any]], int]:
        res = await police_partner_service.list_partners(
            current_user=current_user, keyword=keyword, category=category,
            page=page, page_size=page_size,
        )
        items = []
        for it in (res.get("items") or []):
            items.append({
                "id": it.get("id"),
                "type": "partner",
                "name": it.get("name") or "",
                "description": it.get("description") or "",
                "category": it.get("category") or "协助伙伴",
                "author": it.get("badge_number") or it.get("author") or "社区伙伴",
                "avatar": it.get("icon") or "",
                "tags": it.get("capabilities") or [],
                "apply_mode": "connect",
                "stats": {"usage": 0, "rating": 0, "review_count": 0},
                "created_at": it.get("created_at") or "",
            })
        return items, res.get("total") or 0

    async def _explore_templates(
        self, *, keyword: str | None, category: str | None,
    ) -> list[dict[str, Any]]:
        rows = await police_task_template_service.list_templates(
            enabled_only=True, keyword=keyword,
        )
        items = []
        for it in rows:
            # category 过滤（element_type 作为分类）
            if category and it.get("element_type") != category:
                continue
            items.append({
                "id": it.get("id"),
                "type": "template",
                "name": it.get("name") or "",
                "description": it.get("description") or "",
                "category": it.get("element_type") or "任务模板",
                "author": "小南内置",
                "avatar": "",
                "tags": [it.get("task_type")] if it.get("task_type") else [],
                "apply_mode": "install",
                "stats": {"usage": 0, "rating": 0, "review_count": 0},
                "created_at": it.get("created_at") or "",
            })
        return items

    async def detail(
        self, *, type: str, asset_id: int, current_user: User,
    ) -> dict[str, Any]:
        """资产详情（按类型路由到对应服务）。"""
        if type not in MARKET_TYPES:
            raise ValueError("不支持的资产类型")
        if type == "agent":
            return await police_agent_service.get_agent(asset_id)
        if type == "partner":
            result = await police_partner_service.get_partner(asset_id)
            if not result:
                raise ValueError("协助伙伴不存在")
            return result
        result = await police_task_template_service.get(asset_id)
        if not result:
            raise ValueError("任务模板不存在")
        return result

    # ── 申请使用 ─────────────────────────────────────────

    async def apply(
        self, *, type: str, asset_id: int, current_user: User,
    ) -> dict[str, Any]:
        """按 apply_mode 处理申请：

        - agent → connect：建立 police_agent_connections（不复制警员身份）
        - partner → bind：单独添加建立 binding（幂等，与级联添加同语义，P5）
        - template → install：MVP 仅确认解锁，不复制
        """
        if type == "agent":
            return await police_partner_service.apply_connection(
                agent_id=asset_id, current_user=current_user,
            )
        if type == "partner":
            partner = await police_partner_service.get_partner(asset_id)
            if not partner:
                raise ValueError("协助伙伴不存在")
            # P5：单独添加 = 建立 binding（与数字警员「添加」一致：绑定共享实例不复制）
            conn, _created = await agent_binding_repository.ensure_connection(
                user_id=current_user.id, agent_id=asset_id, status="active",
            )
            await write_audit_log(
                action="connection.apply",
                resource_type="partner",
                resource_id=asset_id,
                user_id=current_user.id,
                user_name=getattr(current_user, "name", None),
                details={"partner_name": partner.get("name")},
            )
            result = conn.to_dict()
            result["agent"] = {"id": asset_id, "name": partner.get("name"),
                               "is_subagent": True}
            result["mode"] = "bind"
            result["message"] = "已添加该协助伙伴，可在「我的数字警员」中管理"
            return result
        template = await police_task_template_service.get(asset_id)
        if not template:
            raise ValueError("任务模板不存在")
        return {
            "ok": True,
            "mode": "install",
            "message": "该侦查模板已解锁，创建任务时可直接选用",
        }

    # ── 发布与审核 ─────────────────────────────────────────

    async def publish(
        self, *, type: str, asset_id: int, reason: str | None,
        current_user: User,
    ) -> dict[str, Any]:
        """发布资产到市场。

        agent/partner → 复用共享体系 global → pending，经超管审批后上架；
        template → MVP 直接 enabled 上架（无审批链）。
        权限：仅创建者或超管可发布。
        """
        if type == "agent":
            agent = await police_agent_repository.get_by_id(asset_id)
            if not agent or agent.is_subagent:
                raise ValueError("数字警员不存在")
            if not user_can_manage_agent(current_user, agent):
                raise PermissionError("仅该数字警员的创建者或超管可发布")
            result = await police_agent_service.share_agent(
                asset_id, scope="global", author_id=current_user.id,
            )
            if not result:
                raise ValueError("发布失败：数字警员不存在")
            status = result.get("approval_status") or "pending"
            await write_audit_log(
                action="market.publish", resource_type="agent", resource_id=asset_id,
                user_id=current_user.id, user_name=getattr(current_user, "name", None),
                details={"type": type, "reason": reason, "status": status},
            )
            return {"ok": True, "status": status,
                    "message": "已提交市场审核，通过后将在市场可见"}

        if type == "partner":
            partner = await police_partner_service.get_partner(asset_id)
            if not partner:
                raise ValueError("协助伙伴不存在")
            # 复用 partner_service 的权限校验路径（share 内部校验创建者）
            result = await police_partner_service.share_partner(
                partner_id=asset_id, scope="global", author_id=current_user.id,
            )
            status = (result or {}).get("approval_status") or "pending"
            await write_audit_log(
                action="market.publish", resource_type="partner", resource_id=asset_id,
                user_id=current_user.id, user_name=getattr(current_user, "name", None),
                details={"type": type, "reason": reason, "status": status},
            )
            return {"ok": True, "status": status,
                    "message": "已提交市场审核，通过后将在市场可见"}

        if type == "template":
            template = await police_task_template_service.get(asset_id)
            if not template:
                raise ValueError("任务模板不存在")
            updated = await police_task_template_service.update(
                asset_id, {"enabled": 1},
            )
            await write_audit_log(
                action="market.publish", resource_type="template", resource_id=asset_id,
                user_id=current_user.id, user_name=getattr(current_user, "name", None),
                details={"type": type, "reason": reason, "status": "published"},
            )
            return {"ok": True, "status": "published",
                    "message": "模板已上架市场" if updated else "模板已上架市场"}

        raise ValueError("不支持的资产类型")

    async def pending(
        self, *, page: int = 1, page_size: int = 50,
    ) -> dict[str, Any]:
        """超管待审列表（数字警员 + 协助伙伴的全局共享申请）。"""
        items: list[dict[str, Any]] = []
        agents, total = await police_agent_repository.list_pending_agents(
            page=page, page_size=page_size,
        )
        for a in agents:
            d = a.to_dict()
            items.append({
                "request_type": "agent",
                "id": a.id,
                "name": a.name,
                "author": d.get("badge_number") or str(a.created_by or ""),
                "status": a.approval_status,
                "requested_at": d.get("updated_at") or "",
            })
        # 协助伙伴待审（is_subagent=true 且 approval_status=pending）
        partner_items = await self._pending_partners()
        items.extend(partner_items)
        return {"items": items, "total": total + len(partner_items), "page": page}

    async def _pending_partners(self) -> list[dict[str, Any]]:
        async with pg_manager.get_async_session_context() as session:
            stmt = (
                select(Agent)
                .where(Agent.is_subagent.is_(True), Agent.approval_status == "pending")
                .order_by(Agent.id.desc())
            )
            result = await session.execute(stmt)
            partners = list(result.scalars().all())
        items = []
        for p in partners:
            items.append({
                "request_type": "partner",
                "id": p.id,
                "name": p.name,
                "author": str(p.created_by or ""),
                "status": p.approval_status,
                "requested_at": "",
            })
        return items

    async def approve(
        self, *, request_type: str, request_id: int, approved: bool,
        reviewer_id: int, reason: str | None = None,
    ) -> dict[str, Any]:
        """超管审批市场申请。template 无审批链（MVP）。reason 为驳回/通过理由，仅入审计。"""
        if request_type == "agent":
            result = await police_agent_service.approve_agent(
                request_id, approved=approved, reviewer_id=reviewer_id,
            )
            if not result:
                raise ValueError("该数字警员无待审批的申请")
        elif request_type == "partner":
            result = await police_partner_service.approve_partner(
                request_id, approved=approved, reviewer_id=reviewer_id,
            )
            if not result:
                raise ValueError("该协助伙伴无待审批的申请")
        else:
            raise ValueError("模板无审批流程（MVP）")

        await write_audit_log(
            action="market.approve", resource_type=request_type, resource_id=request_id,
            user_id=reviewer_id, details={"approved": approved, "reason": reason},
        )
        return {"ok": True, "status": "approved" if approved else "rejected"}


police_market_service = PoliceMarketService()
