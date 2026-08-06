"""★ 工作台能力演进 / 智能孵化聚合服务（模块 G+F）

复用 police_dashboard_service 之外新增的两个 Tab 数据源：
- get_evolution：技能诊断（任务模板命中/成功率）、连接器、协助伙伴高频协作 Top3
- get_incubation：当前用户创建的数字民警列表 + 完成度

全部基于现有表统计（police_tasks / police_task_templates / police_agent_runs / agents），不引入新表。
"""

from typing import Any

from sqlalchemy import select, func

from yuxi.repositories.police_agent_repository import police_agent_repository
from yuxi.services.police_task_template_service import police_task_template_service
from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_business import Agent, User
from yuxi.storage.postgres.models_police import PoliceAgentRun, PoliceTask

# 完成度权重（文档 §F：灵魂20% + 技能30% + 连接器20% + 审批30%）
_COMPLETENESS_WEIGHTS = {
    "soul": 20,
    "skills": 30,
    "connectors": 20,
    "approval": 30,
}


class PoliceEvolutionService:
    """能力演进 + 智能孵化数据聚合。"""

    # ── 能力演进 ─────────────────────────────────────────

    async def get_evolution(self, current_user: User) -> dict[str, Any]:
        """能力演进三块：技能诊断 / 连接器 / 协助伙伴。无数据时返回空数组/0。"""
        async with pg_manager.get_async_session_context() as session:
            # 任务按类型统计（模板命中 = extra.advancement 带 template_id 的任务）
            task_rows = list((await session.execute(
                select(PoliceTask.type, PoliceTask.status, PoliceTask.extra)
            )).all())
            # 运行记录（协助伙伴高频协作）
            run_rows = list((await session.execute(
                select(PoliceAgentRun.agent_id, PoliceAgentRun.status)
            )).all())

        # 技能诊断：模板总数 + 任务命中/成功率
        templates = await police_task_template_service.list_templates(enabled_only=True)
        template_ids = {t.get("id") for t in templates}
        hit_count = sum(1 for _, _, extra in task_rows if self._task_used_template(extra, template_ids))
        total_tasks = len(task_rows)
        completed = sum(1 for _, status, _ in task_rows if status == "completed")
        success_rate = round(completed / total_tasks * 100, 1) if total_tasks else 0
        # 低命中模板（启用但从未被命中）
        low_hit = [t for t in templates if t.get("id") not in {
            self._task_template_id(extra) for _, _, extra in task_rows if extra
        }][:5]

        # 连接器：当前无 MCP 统计源，返回启用占位
        connectors = {"enabled_count": 0, "success_rate": 0, "offline": []}

        # 协助伙伴：按 agent_id 聚合运行次数 Top3
        run_counter: dict[int, int] = {}
        for agent_id, _ in run_rows:
            if agent_id is not None:
                run_counter[agent_id] = run_counter.get(agent_id, 0) + 1
        top_ids = sorted(run_counter, key=run_counter.get, reverse=True)[:3]
        partners = []
        for aid in top_ids:
            agent = await police_agent_repository.get_by_id(aid)
            if agent:
                partners.append({
                    "agent_id": aid,
                    "name": agent.name,
                    "run_count": run_counter[aid],
                })

        return {
            "skill_diagnostics": {
                "template_count": len(templates),
                "hit_count": hit_count,
                "success_rate": success_rate,
                "total_tasks": total_tasks,
                "low_hit_templates": low_hit,
            },
            "connectors": connectors,
            "partners": partners,
        }

    @staticmethod
    def _task_used_template(extra: dict | None, template_ids: set[int]) -> bool:
        tid = PoliceEvolutionService._task_template_id(extra)
        return tid is not None and tid in template_ids

    @staticmethod
    def _task_template_id(extra: dict | None) -> int | None:
        if not extra:
            return None
        adv = extra.get("advancement") if isinstance(extra, dict) else None
        if isinstance(adv, dict):
            return adv.get("template_id")
        return extra.get("template_id")

    # ── 智能孵化 ─────────────────────────────────────────

    async def get_incubation(self, current_user: User) -> dict[str, Any]:
        """当前用户创建的数字民警列表（含完成度），供智能孵化 Tab 展示。"""
        async with pg_manager.get_async_session_context() as session:
            stmt = (
                select(Agent)
                .where(Agent.is_subagent.is_(False), Agent.created_by == str(current_user.uid))
                .order_by(Agent.id.desc())
            )
            agents = list((await session.execute(stmt)).scalars().all())

        items = []
        for a in agents:
            d = a.to_dict()
            items.append({
                "id": a.id,
                "name": a.name,
                "badge_number": d.get("badge_number") or "",
                "description": d.get("description") or a.description or "",
                "status": a.status or "draft",
                "approval_status": a.approval_status,
                "completeness": await self.completeness_of(a),
                "updated_at": d.get("updated_at") or "",
            })
        return {"items": items, "total": len(items)}

    async def completeness_of(self, agent: Agent) -> dict[str, Any]:
        """完成度：灵魂20 / 技能30 / 连接器20 / 审批30，附推荐下一步。"""
        d = agent.to_dict()
        parts = {
            "soul": 0 if not (agent.system_prompt or d.get("system_prompt")) else _COMPLETENESS_WEIGHTS["soul"],
            "skills": min(len(d.get("skills") or []) * 10, _COMPLETENESS_WEIGHTS["skills"]),
            "connectors": min(len(d.get("tools") or d.get("tool_ids") or []) * 10, _COMPLETENESS_WEIGHTS["connectors"]),
            "approval": _COMPLETENESS_WEIGHTS["approval"] if agent.approval_status == "approved" else 0,
        }
        total = sum(parts.values())
        next_steps = []
        if parts["soul"] == 0:
            next_steps.append("补充灵魂（系统提示词）")
        if parts["skills"] < _COMPLETENESS_WEIGHTS["skills"]:
            next_steps.append("补充技能")
        if parts["approval"] == 0 and agent.approval_status != "approved":
            next_steps.append("提交全局审批")
        return {"percent": total, "parts": parts, "next_steps": next_steps[:3]}

    async def completeness(self, agent_id: int) -> dict[str, Any] | None:
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            return None
        return await self.completeness_of(agent)


police_evolution_service = PoliceEvolutionService()
