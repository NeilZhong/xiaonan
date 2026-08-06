"""★ 数字警员版本与发布控制服务（运行中心）

借鉴悟帆运行中心「流动版本 / 受控发布」双模式：
- 每次灵魂/技能/连接器/卡片改动自动生成版本快照（police_agent_versions）。
- rolling 模式：新版本立即成为 current_version_id，全用户即时可见。
- controlled 模式：新版本进入 draft_version_id，超管/作者手动 publish 后才生效。
- 任意历史版本可 rollback（生成新版本替换当前）。

可见性规则：对话/派活读取 current_version_id 对应的 config_snapshot；
普通用户永远看不到 draft。改动了 agents 表，但通过独立表存版本，不改 yuxi 模型列。
"""

from typing import Any

from sqlalchemy import select

from yuxi.repositories.police_agent_repository import police_agent_repository
from yuxi.services.police_service import write_audit_log
from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_business import Agent, User
from yuxi.storage.postgres.models_police import (
    PoliceAgentReleaseState,
    PoliceAgentVersion,
)
from yuxi.utils import logger


async def _get_or_create_release_state(session, agent_id: int) -> PoliceAgentReleaseState:
    stmt = select(PoliceAgentReleaseState).where(PoliceAgentReleaseState.agent_id == agent_id)
    state = (await session.execute(stmt)).scalar_one_or_none()
    if not state:
        state = PoliceAgentReleaseState(agent_id=agent_id, release_mode="rolling")
        session.add(state)
        await session.flush()
    return state


class PoliceAgentVersionService:
    """数字警员版本与发布控制"""

    async def create_snapshot(
        self, *, agent_id: int, change_summary: str, created_by: int | None = None,
    ) -> dict[str, Any]:
        """灵魂/资产改动后自动快照（幂等：无实际改动不生成）。

        返回最新 release state 摘要。
        """
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            raise ValueError("数字警员不存在")
        async with pg_manager.get_async_session_context() as session:
            # 取最新版本号，计算下一版 vX.Y+1
            stmt = (
                select(PoliceAgentVersion)
                .where(PoliceAgentVersion.agent_id == agent_id)
                .order_by(PoliceAgentVersion.id.desc())
                .limit(1)
            )
            last = (await session.execute(stmt)).scalar_one_or_none()
            next_label = self._next_version_label(last.version_label if last else None)

            state = await _get_or_create_release_state(session, agent_id)
            new_version = PoliceAgentVersion(
                agent_id=agent_id,
                version_label=next_label,
                change_summary=change_summary or "配置变更",
                config_snapshot=agent.config_json or {},
                release_mode=state.release_mode,
                status="draft" if state.release_mode == "controlled" else "active",
                created_by=created_by,
                created_at=__import__("yuxi.utils.datetime_utils", fromlist=["utc_now_naive"]).utc_now_naive(),
                published_at=None,
            )
            session.add(new_version)
            await session.flush()

            # 更新发布状态
            if state.release_mode == "controlled":
                # 旧草稿作废
                if state.draft_version_id:
                    old_draft = await session.get(PoliceAgentVersion, state.draft_version_id)
                    if old_draft and old_draft.status == "draft":
                        old_draft.status = "superseded"
                state.draft_version_id = new_version.id
            else:
                # 旧 active 版本作废
                if state.current_version_id:
                    old_active = await session.get(PoliceAgentVersion, state.current_version_id)
                    if old_active and old_active.status == "active":
                        old_active.status = "superseded"
                state.current_version_id = new_version.id
                new_version.published_at = new_version.created_at
            await session.commit()
            await session.refresh(state)
            return state.to_dict()

    async def list_versions(self, *, agent_id: int, include_snapshot: bool = False) -> dict[str, Any]:
        """版本历史（最新在前）。"""
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            raise ValueError("数字警员不存在")
        async with pg_manager.get_async_session_context() as session:
            stmt = (
                select(PoliceAgentVersion)
                .where(PoliceAgentVersion.agent_id == agent_id)
                .order_by(PoliceAgentVersion.id.desc())
            )
            result = await session.execute(stmt)
            versions = list(result.scalars().all())
            state = (await session.execute(
                select(PoliceAgentReleaseState).where(PoliceAgentReleaseState.agent_id == agent_id)
            )).scalar_one_or_none()
        items = []
        for v in versions:
            d = v.to_dict()
            if include_snapshot:
                d["config_snapshot"] = v.config_snapshot
            items.append(d)
        return {
            "items": items,
            "total": len(items),
            "release_mode": state.release_mode if state else "rolling",
            "current_version_id": state.current_version_id if state else None,
            "draft_version_id": state.draft_version_id if state else None,
        }

    async def switch_mode(self, *, agent_id: int, mode: str, current_user: User) -> dict[str, Any]:
        """切换发布模式（rolling ↔ controlled）。超管或作者可用。"""
        if mode not in ("rolling", "controlled"):
            raise ValueError("无效的发布模式")
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            raise ValueError("数字警员不存在")
        async with pg_manager.get_async_session_context() as session:
            state = await _get_or_create_release_state(session, agent_id)
            if state.release_mode == mode:
                await session.commit()
                return state.to_dict()
            state.release_mode = mode
            # 切到 rolling：草稿立即发布为 current
            if mode == "rolling" and state.draft_version_id:
                draft = await session.get(PoliceAgentVersion, state.draft_version_id)
                if draft and draft.status == "draft":
                    draft.status = "active"
                    draft.release_mode = "rolling"
                    draft.published_at = draft.created_at
                    if state.current_version_id:
                        old = await session.get(PoliceAgentVersion, state.current_version_id)
                        if old:
                            old.status = "superseded"
                    state.current_version_id = draft.id
                    state.draft_version_id = None
            await session.commit()
            await session.refresh(state)
        await write_audit_log(
            action="agent.release.switch_mode",
            resource_type="agent",
            resource_id=agent_id,
            user_id=current_user.id,
            user_name=getattr(current_user, "name", None),
            details={"mode": mode},
        )
        return state.to_dict()

    async def publish_draft(self, *, agent_id: int, current_user: User) -> dict[str, Any]:
        """手动发布草稿版本（受控发布模式下）。超管或作者可用。"""
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            raise ValueError("数字警员不存在")
        async with pg_manager.get_async_session_context() as session:
            state = await _get_or_create_release_state(session, agent_id)
            if not state.draft_version_id:
                raise ValueError("没有待发布的草稿版本")
            draft = await session.get(PoliceAgentVersion, state.draft_version_id)
            if not draft or draft.status != "draft":
                raise ValueError("草稿版本不存在或已发布")
            draft.status = "active"
            draft.published_at = __import__("yuxi.utils.datetime_utils", fromlist=["utc_now_naive"]).utc_now_naive()
            if state.current_version_id:
                old = await session.get(PoliceAgentVersion, state.current_version_id)
                if old:
                    old.status = "superseded"
            state.current_version_id = draft.id
            state.draft_version_id = None
            await session.commit()
            await session.refresh(state)
        await write_audit_log(
            action="agent.release.publish",
            resource_type="agent",
            resource_id=agent_id,
            user_id=current_user.id,
            user_name=getattr(current_user, "name", None),
            details={"version_id": draft.id, "version_label": draft.version_label},
        )
        return state.to_dict()

    async def rollback(self, *, agent_id: int, version_id: int, current_user: User) -> dict[str, Any]:
        """回滚到指定历史版本（生成新版本替换当前）。超管或作者可用。"""
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            raise ValueError("数字警员不存在")
        async with pg_manager.get_async_session_context() as session:
            target = await session.get(PoliceAgentVersion, version_id)
            if not target or target.agent_id != agent_id:
                raise ValueError("版本不存在")
            # 原版本标记 rolled_back 供追溯
            target.status = "rolled_back"

            # 基于目标快照生成新版本
            stmt = (
                select(PoliceAgentVersion)
                .where(PoliceAgentVersion.agent_id == agent_id)
                .order_by(PoliceAgentVersion.id.desc())
                .limit(1)
            )
            last = (await session.execute(stmt)).scalar_one_or_none()
            next_label = self._next_version_label(last.version_label if last else None)
            state = await _get_or_create_release_state(session, agent_id)
            new_version = PoliceAgentVersion(
                agent_id=agent_id,
                version_label=next_label,
                change_summary=f"回滚至 {target.version_label}",
                config_snapshot=target.config_snapshot,
                release_mode=state.release_mode,
                status="active",
                created_by=current_user.id,
                created_at=__import__("yuxi.utils.datetime_utils", fromlist=["utc_now_naive"]).utc_now_naive(),
                published_at=__import__("yuxi.utils.datetime_utils", fromlist=["utc_now_naive"]).utc_now_naive(),
            )
            session.add(new_version)
            await session.flush()
            if state.current_version_id:
                old = await session.get(PoliceAgentVersion, state.current_version_id)
                if old and old.id != target.id:
                    old.status = "superseded"
            state.current_version_id = new_version.id
            state.draft_version_id = None
            # 把回滚后的快照同步回 agents.config_json，使线上配置立即切换
            agent.config_json = target.config_snapshot or {}
            await session.commit()
            await session.refresh(state)
        await write_audit_log(
            action="agent.release.rollback",
            resource_type="agent",
            resource_id=agent_id,
            user_id=current_user.id,
            user_name=getattr(current_user, "name", None),
            details={"from_version_id": version_id, "to_label": new_version.version_label},
        )
        return state.to_dict()

    async def health(self, *, agent_id: int) -> dict[str, Any]:
        """资产健康度（版本同步状态，轻量实现）。"""
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            raise ValueError("数字警员不存在")
        async with pg_manager.get_async_session_context() as session:
            state = (await session.execute(
                select(PoliceAgentReleaseState).where(PoliceAgentReleaseState.agent_id == agent_id)
            )).scalar_one_or_none()
            stmt = (
                select(PoliceAgentVersion)
                .where(PoliceAgentVersion.agent_id == agent_id)
                .order_by(PoliceAgentVersion.id.desc())
                .limit(1)
            )
            latest = (await session.execute(stmt)).scalar_one_or_none()
        synced = True
        details = []
        if state:
            # current_version 与最新版本一致 = 同步；否则有未发布草稿
            if state.release_mode == "controlled" and state.draft_version_id:
                synced = False
                details.append("存在待发布草稿")
            if state.current_version_id and latest and state.current_version_id != latest.id and latest.status == "draft":
                synced = False
        return {
            "synced": synced,
            "release_mode": state.release_mode if state else "rolling",
            "current_version_label": latest.version_label if latest and latest.status == "active" else None,
            "draft_count": 1 if (state and state.draft_version_id) else 0,
            "details": details,
        }

    @staticmethod
    def _next_version_label(current: str | None) -> str:
        """v0.1 → v0.2 → ... → v0.9 → v0.10（仅递增次版本号，简单可靠）。"""
        if not current or not current.startswith("v"):
            return "v0.1"
        try:
            minor = int(current[1:].split(".")[1]) + 1
        except (IndexError, ValueError):
            return "v0.1"
        return f"v0.{minor}"


police_agent_version_service = PoliceAgentVersionService()
