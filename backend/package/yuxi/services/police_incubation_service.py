"""★ 数字民警智能孵化服务（模块 F）

从零孵化 / 继续打磨：
- create_draft：根据描述规则化生成数字民警草案（名称/灵魂/推荐技能/完成度），不落库，
  前端确认后调用现有 police_agent_service.create_agent 写入（status=draft）。
- list_drafts / completeness / refine：草稿列表、完成度、优化建议。

LLM 深度生成预留：模型（agnes base_url）未配置时用规则化模板兜底，保证功能可用。
"""

from typing import Any
import re

from yuxi.repositories.police_agent_repository import police_agent_repository
from yuxi.services.police_evolution_service import police_evolution_service
from yuxi.services.police_task_template_service import police_task_template_service
from yuxi.storage.postgres.models_business import User

class PoliceIncubationService:
    """智能孵化：草案生成（规则化） + 草稿列表 / 完成度 / 优化建议。"""

    async def create_draft(
        self, *, description: str, target_users: str | None = None,
        responsibilities: str | None = None, usage_scenarios: str | None = None,
        model_hint: str | None = None, current_user: User,
    ) -> dict[str, Any]:
        """从零孵化：生成可确认的数字民警草案（不落库）。"""
        desc = (description or "").strip()
        if len(desc) < 4:
            raise ValueError("请先描述想孵化的数字民警（服务谁、负责什么、在哪里用）")

        name = self._derive_name(desc)
        system_prompt = self._build_system_prompt(desc, target_users, responsibilities, usage_scenarios)
        recommended_skills = await self._match_skills(desc)

        draft = {
            "name": name,
            "description": desc[:300],
            "department_tag": self._derive_department(desc),
            "system_prompt": system_prompt,
            "recommended_skills": recommended_skills,
            "model_hint": model_hint or "",
            "completeness": {
                "percent": 30,
                "parts": {"soul": 20, "skills": 10, "connectors": 0, "approval": 0},
                "next_steps": ["补充技能", "提交全局审批"],
            },
        }
        return {"ok": True, "draft": draft,
                "message": "草案已生成，确认后将写入数字民警（草稿状态）"}

    async def list_drafts(self, current_user: User) -> dict[str, Any]:
        """当前用户创建的数字民警草稿（含完成度）。"""
        return await police_evolution_service.get_incubation(current_user)

    async def completeness(self, agent_id: int) -> dict[str, Any] | None:
        """单个数字民警完成度。"""
        return await police_evolution_service.completeness(agent_id)

    async def refine(
        self, *, agent_id: int, feedback: str, focus: str = "all",
        current_user: User,
    ) -> dict[str, Any]:
        """继续打磨：基于反馈生成优化建议（MVP 规则化，确认后由前端调用 update_agent 应用）。"""
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            raise ValueError("数字民警不存在")
        feedback_text = (feedback or "").strip()
        if not feedback_text:
            raise ValueError("请填写优化反馈")
        suggestion = (
            f"将以下反馈合并到{'灵魂（system_prompt）' if focus == 'soul' else '技能/能力配置' if focus == 'skills' else '完整配置'}"
            f"：{feedback_text[:200]}"
        )
        return {
            "ok": True,
            "agent_id": agent_id,
            "focus": focus,
            "suggestion": suggestion,
            "message": "优化建议已生成（规则化 MVP），确认后可在档案页编辑应用",
        }

    # ── 规则化生成助手 ─────────────────────────────────────

    @staticmethod
    def _derive_name(desc: str) -> str:
        """从描述抽取名称：优先「角色词短语」，其次引号内内容。"""
        # 引号内优先
        for mark in ("「", "『", "\""):
            start = desc.find(mark)
            if start >= 0:
                end = desc.find("」" if mark in ("「", "『") else "\"", start + 1)
                if end > start:
                    inner = desc[start + 1:end].strip()
                    if inner:
                        return inner[:20]
        # 角色词：向前找最近分隔符作为短语起点（最多前 6 个汉字）
        m = re.search(r"(?:民警|助手|专家|分析师|专员|审核官)", desc)
        if m:
            idx = m.start()
            seg = desc[:idx]
            cut = max(seg.rfind("，"), seg.rfind("。"), seg.rfind("、"), seg.rfind("的"))
            start = cut + 1 if cut >= 0 else max(0, idx - 6)
            phrase = desc[start:idx + len(m.group(0))].strip()
            if phrase:
                return phrase[:20]
        return "智能孵化民警"

    @staticmethod
    def _derive_department(desc: str) -> str:
        for kw in ("刑侦", "经侦", "网安", "治安", "法制", "缉毒", "禁毒"):
            if kw in desc:
                return kw + "支队"
        return "综合"

    @staticmethod
    def _build_system_prompt(
        desc: str, target_users: str | None,
        responsibilities: str | None, usage_scenarios: str | None,
    ) -> str:
        parts = [
            "你是小南平台的一名数字民警（公安多智能体协作平台专业智能体）。",
            f"服务对象：{target_users or '一线办案民警'}。",
            f"主要职责：{responsibilities or desc[:120]}。",
            f"典型场景：{usage_scenarios or '案件办理过程中的专业分析与协同'}。",
            "工作原则：基于证据、程序合规、结论可审计；输出结构化、可直接落地的材料。",
        ]
        return "\n".join(parts)

    async def _match_skills(self, desc: str) -> list[dict[str, Any]]:
        """按描述关键词与启用模板匹配推荐技能（Top 3）。"""
        templates = await police_task_template_service.list_templates(enabled_only=True)
        scored = []
        for t in templates:
            text = f"{t.get('name') or ''} {t.get('description') or ''} {t.get('task_type') or ''}"
            score = sum(1 for ch in desc if ch in text and ch not in "的了我是在和有与及")
            if score >= 2:
                scored.append((score, t))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "template_id": t.get("id"),
                "name": t.get("name"),
                "task_type": t.get("task_type"),
            }
            for _, t in scored[:3]
        ]


police_incubation_service = PoliceIncubationService()
