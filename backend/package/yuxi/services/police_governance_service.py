"""★ 治理后台服务（P3）——审核台 + 运行中心

数字警察与协助伙伴走统一治理流水线：用户创建 → 管理员审核（看全设定 + 对话试跑）→ 探索市场上架。

- 审核台：聚合待审项、展示全量配置、以草稿配置试跑预览对话、通过/驳回（含理由）。
- 运行中心：平台默认运行模式读写（默认受控发布）、各智能体在线状态/绑定规模/当前模式总览。

权限统一在路由层用 get_superadmin_user 把关；本服务只负责编排与留痕。
"""

from typing import Any

from sqlalchemy import func, select

from yuxi.repositories.police_agent_repository import police_agent_repository
from yuxi.repositories.police_binding_repository import (
    agent_associated_partner_repository,
    agent_binding_repository,
)
from yuxi.services.police_market_service import police_market_service
from yuxi.services.police_service import write_audit_log
from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_business import Agent, User
from yuxi.storage.postgres.models_police import (
    PoliceAgentReleaseState,
    PoliceAgentVersion,
    PoliceGovernanceConfig,
)
from yuxi.utils import logger

RELEASE_MODES = ("rolling", "controlled")
DEFAULT_RELEASE_MODE = "controlled"

# 单行配置表的固定主键，避免多行歧义
_CONFIG_ROW_ID = 1


async def get_default_release_mode() -> str:
    """平台默认运行模式；配置行缺失时回落受控发布（最保守语义）。"""
    try:
        async with pg_manager.get_async_session_context() as session:
            row = await session.get(PoliceGovernanceConfig, _CONFIG_ROW_ID)
            return row.default_release_mode if row else DEFAULT_RELEASE_MODE
    except Exception as e:
        logger.warning(f"读取平台默认运行模式失败，回落 controlled: {e}")
        return DEFAULT_RELEASE_MODE


class PoliceGovernanceService:
    """治理后台：审核台与运行中心"""

    # ── 审核台 ────────────────────────────────────────────

    async def review_pending(self, *, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        """待审列表：新建待审 + 全局共享申请，统一结构按提交时间倒序。

        数字警员与协助伙伴同为 agents 表记录，用 is_subagent 派生 request_type。
        """
        agents, total = await police_agent_repository.list_pending_agents(
            page=page, page_size=page_size,
        )
        items = []
        for a in agents:
            d = a.to_dict()
            items.append({
                "request_type": "partner" if a.is_subagent else "agent",
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "icon": d.get("icon"),
                "category": a.category,
                "share_level": (d.get("share_config") or {}).get("access_level"),
                "created_by": a.created_by,
                "status": a.approval_status,
                "requested_at": d.get("updated_at") or d.get("created_at") or "",
            })
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def review_detail(self, *, agent_id: int) -> dict[str, Any]:
        """待审详情：全量配置 + 关联伙伴 + 版本基线（当前/草稿）。"""
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            raise ValueError("智能体不存在")

        associations = await agent_associated_partner_repository.list_associations(agent_id)
        partners = [
            {"id": p.id, "name": p.name, "category": p.category,
             "approval_status": p.approval_status}
            for _, p in associations
        ]

        async with pg_manager.get_async_session_context() as session:
            state = (await session.execute(
                select(PoliceAgentReleaseState).where(PoliceAgentReleaseState.agent_id == agent_id)
            )).scalar_one_or_none()
            versions = list((await session.execute(
                select(PoliceAgentVersion)
                .where(PoliceAgentVersion.agent_id == agent_id)
                .order_by(PoliceAgentVersion.id.desc())
                .limit(10)
            )).scalars().all())

        return {
            "agent": agent.to_dict(),
            "runtime": {
                "system_prompt": agent.system_prompt,
                "model_config": agent.model_config,
                "tools": agent.tools or [],
                "skills": agent.skills or [],
                "knowledge_base_ids": agent.knowledge_base_ids or [],
            },
            "associated_partners": partners,
            "release_mode": state.release_mode if state else await get_default_release_mode(),
            "current_version_id": state.current_version_id if state else None,
            "draft_version_id": state.draft_version_id if state else None,
            "versions": [v.to_dict() for v in versions],
        }

    async def review_decide(
        self, *, request_type: str, request_id: int, approved: bool,
        reason: str | None, current_user: User,
    ) -> dict[str, Any]:
        """审核通过/驳回。状态流转复用市场审批（幂等：非 pending 会报错），此处补记理由。"""
        result = await police_market_service.approve(
            request_type=request_type, request_id=request_id,
            approved=approved, reviewer_id=current_user.id, reason=reason,
        )
        result["reason"] = reason
        return result

    async def preview_run(
        self, *, agent_id: int, message: str, use_draft: bool = True,
    ) -> dict[str, Any]:
        """以草稿配置试跑单轮对话，不写任何运行记录，避免污染案件追溯与统计。

        草稿不可用时降级为当前配置并附 warning，不阻断审核动作。
        """
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            raise ValueError("智能体不存在")
        if not (message or "").strip():
            raise ValueError("试跑内容不能为空")

        system_prompt, config_source, warning = await self._resolve_preview_prompt(
            agent=agent, agent_id=agent_id, use_draft=use_draft,
        )

        from langchain_core.messages import HumanMessage, SystemMessage

        from yuxi.agents.models import load_chat_model, resolve_chat_model_spec

        # 回显真实生效的模型（警员未配模型时会落到平台默认），便于审核员判断试跑可信度
        model_spec = resolve_chat_model_spec(self._model_spec(agent))
        model = load_chat_model(model_spec)
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=message))
        response = await model.ainvoke(messages)

        return {
            "reply": getattr(response, "content", "") or "",
            "config_source": config_source,
            "model": model_spec,
            "warning": warning,
        }

    async def _resolve_preview_prompt(
        self, *, agent: Agent, agent_id: int, use_draft: bool,
    ) -> tuple[str | None, str, str | None]:
        """解析试跑所用系统提示词，返回 (prompt, 来源, 告警)。"""
        if not use_draft:
            return agent.system_prompt, "current", None

        async with pg_manager.get_async_session_context() as session:
            state = (await session.execute(
                select(PoliceAgentReleaseState).where(PoliceAgentReleaseState.agent_id == agent_id)
            )).scalar_one_or_none()
            draft = (
                await session.get(PoliceAgentVersion, state.draft_version_id)
                if state and state.draft_version_id else None
            )

        if not draft:
            return agent.system_prompt, "current", None

        snapshot = draft.config_snapshot or {}
        prompt = (snapshot.get("context") or {}).get("system_prompt")
        if not prompt:
            return agent.system_prompt, "current", "草稿配置不可用，已回落当前配置试跑"
        return prompt, "draft", None

    @staticmethod
    def _model_spec(agent: Agent) -> str | None:
        """由 agent.model_config 拼出 '{provider}:{model}'；缺失则交由平台默认模型。"""
        cfg = agent.model_config or {}
        provider, model = cfg.get("provider"), cfg.get("model")
        return f"{provider}:{model}" if provider and model else None

    # ── 运行中心 ──────────────────────────────────────────

    async def get_runtime_config(self) -> dict[str, Any]:
        """平台级运行配置（当前仅默认运行模式）。"""
        async with pg_manager.get_async_session_context() as session:
            row = await session.get(PoliceGovernanceConfig, _CONFIG_ROW_ID)
            if row:
                return row.to_dict()
        return {"default_release_mode": DEFAULT_RELEASE_MODE, "updated_by": None, "updated_at": None}

    async def set_runtime_config(
        self, *, default_release_mode: str, current_user: User,
    ) -> dict[str, Any]:
        """设置平台默认运行模式（仅影响此后新建智能体的初始发布状态）。"""
        if default_release_mode not in RELEASE_MODES:
            raise ValueError("无效的运行模式")

        async with pg_manager.get_async_session_context() as session:
            row = await session.get(PoliceGovernanceConfig, _CONFIG_ROW_ID)
            if not row:
                row = PoliceGovernanceConfig(id=_CONFIG_ROW_ID)
                session.add(row)
            row.default_release_mode = default_release_mode
            row.updated_by = current_user.id
            await session.commit()
            await session.refresh(row)
            result = row.to_dict()

        await write_audit_log(
            action="governance.runtime_config.update",
            resource_type="governance", resource_id=None,
            user_id=current_user.id, user_name=getattr(current_user, "name", None),
            details={"default_release_mode": default_release_mode},
        )
        return result

    async def runtime_overview(self, *, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        """状态总览：智能体 + 在线状态 + 当前运行模式 + 待发布草稿 + 绑定数。"""
        default_mode = await get_default_release_mode()
        binding_counts = await agent_binding_repository.count_active_by_agent()

        async with pg_manager.get_async_session_context() as session:
            rows = list((await session.execute(
                select(Agent, PoliceAgentReleaseState)
                .outerjoin(PoliceAgentReleaseState, PoliceAgentReleaseState.agent_id == Agent.id)
                .order_by(Agent.id.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )).all())
            total = (await session.execute(
                select(func.count()).select_from(Agent)
            )).scalar() or 0

        items = []
        for agent, state in rows:
            items.append({
                "id": agent.id,
                "name": agent.name,
                "badge_number": agent.badge_number,
                "is_subagent": agent.is_subagent,
                "is_system": agent.is_system,
                "status": agent.status or "active",
                "approval_status": agent.approval_status,
                "release_mode": state.release_mode if state else default_mode,
                "draft_pending": bool(state and state.draft_version_id),
                "current_version_id": state.current_version_id if state else None,
                "binding_count": binding_counts.get(agent.id, 0),
            })
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "default_release_mode": default_mode,
        }


police_governance_service = PoliceGovernanceService()
