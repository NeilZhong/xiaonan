"""★ 案件推进智能体服务 — 多智能体协作架构核心 (POLICE_REQUIREMENTS §6.7)

推进智能体是「建议者 / 推进者」：在任务完成（主办民警审核通过）后读取成果、提取涉案
要素、生成任务草案，经主办民警审查确认后生效。每案件一个逻辑实例，由
case.advancement_enabled 控制开关（1=启用，0=手动模式）。

设计要点：
  - 事件驱动：仅在任务被主办民警审核通过（completed）时触发，不轮询。
  - 不替主办民警决策：生成的草案均为 pending_confirmation 状态，须逐条审查。
  - 可审计可解释：每次推进写入 police_advancement_logs，附带完整上下文与 reasoning。
  - 失败隔离：LLM 调用异常不影响主流程（best-effort + 异常捕获）。
"""

from __future__ import annotations

import json
import re
from typing import Any

from yuxi.repositories.case_repository import case_repository
from yuxi.repositories.task_repository import task_repository
from yuxi.services.police_prompts import (
    ADVANCEMENT_DRAFT_USER_PROMPT,
    ADVANCEMENT_SYSTEM_PROMPT,
)
from yuxi.services.police_service import write_audit_log
from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_police import PoliceAdvancementLog
from yuxi.utils import logger


def _extract_json(text: str) -> dict[str, Any]:
    """从 LLM 输出中提取 JSON 对象（容忍 ```json 代码块包裹与多余文字）。"""
    text = (text or "").strip()
    if not text:
        return {}
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
    return {}


def _build_case_context(case) -> str:
    return (
        f"案件：{case.title}（#{case.id}）\n"
        f"类型：{case.case_type or '未知'}\n"
        f"当前阶段：{case.phase or 'research'}\n"
        f"{case.description or ''}"
    )


class PoliceAdvancementService:
    """案件推进智能体。

    所有公开方法均为协程；advance_after_task_completed 设计为后台任务调用。
    """

    async def advance_after_task_completed(
        self, case_id: int, completed_task_id: int, user_id: int | None = None
    ) -> None:
        """推进智能体主入口：任务完成（主办民警审核通过）后触发。

        读取上下文 → LLM 生成任务草案 → 写入 pending_confirmation 任务 → 记录决策日志
        → 阶段推进自检。作为后台任务调用，不阻塞审核响应。
        """
        try:
            case = await case_repository.get_by_id(case_id)
            if not case:
                return
            if getattr(case, "advancement_enabled", 1) != 1:
                return  # 手动模式：不自动推进

            source_task = await task_repository.get_by_id(completed_task_id)
            if not source_task:
                return

            drafts = await self._generate_drafts(case, source_task)
            proposed = drafts.get("proposed_tasks") or []
            reasoning = drafts.get("reasoning", "")

            created_ids: list[int] = []
            for d in proposed:
                title = (d.get("title") or "").strip()
                if not title:
                    continue
                new_task = await task_repository.create({
                    "case_id": case_id,
                    "title": title,
                    "type": d.get("type") or "investigation",
                    "status": "pending_confirmation",
                    "creator_type": "agent",
                    "creator_id": None,
                    "assignee_type": "human",  # 草案默认未分配，确认后由民警分配
                    "assignee_id": None,
                    "priority": d.get("priority") or "medium",
                    "phase": case.phase or source_task.phase,
                    "instructions": d.get("basis") or "",
                    "parent_task_id": completed_task_id,
                    "extra": {
                        "advancement": {
                            "source_task_id": completed_task_id,
                            "suggested_assignee": d.get("suggested_assignee"),
                        }
                    },
                })
                await task_repository.create_event({
                    "case_id": case_id,
                    "task_id": new_task.id,
                    "event_type": "created",
                    "event_data": {
                        "auto_created": True,
                        "creator_type": "agent",
                        "parent_task_id": completed_task_id,
                    },
                    "created_by": None,
                })
                created_ids.append(new_task.id)

            await self._log_decision(
                case_id=case_id,
                trigger_task_id=completed_task_id,
                decision_type="task_draft",
                summary=(
                    "生成 %d 条任务草案" % len(created_ids)
                )
                if created_ids
                else "评估后暂无需新任务",
                details={
                    "direction": getattr(case, "investigation_direction", None),
                    "generated_task_ids": created_ids,
                    "reasoning": reasoning,
                    "source_task_title": source_task.title,
                },
            )
            await self._maybe_advance_phase(case)
        except Exception as e:
            logger.error(f"Advancement after task {completed_task_id} failed: {e}")

    async def _generate_drafts(self, case, source_task) -> dict[str, Any]:
        """调用 LLM 生成任务草案 JSON（基于单一完成任务）。"""
        try:
            from yuxi.agents.models import load_chat_model
        except Exception as e:  # pragma: no cover - 模型不可用时不阻塞
            logger.warning(f"load_chat_model unavailable: {e}")
            return {}

        existing, _ = await task_repository.list_tasks(case_id=case.id, limit=200)
        existing_lines = [
            f"- [{t.status}] {t.title}（{t.type}）"
            for t in existing
            if t.id != source_task.id
        ]
        existing_text = "\n".join(existing_lines) if existing_lines else "（暂无）"

        result = source_task.result or {}
        result_text = json.dumps(result, ensure_ascii=False, indent=2)
        if len(result_text) > 4000:
            result_text = result_text[:4000] + "\n...（已截断）"

        user_prompt = ADVANCEMENT_DRAFT_USER_PROMPT.format(
            case_context=_build_case_context(case),
            direction=getattr(case, "investigation_direction", None) or "（未指定，按常规侦查逻辑）",
            completed_task_title=source_task.title,
            completed_task_type=source_task.type,
            completed_result=result_text,
            existing_tasks=existing_text,
        )

        try:
            model = load_chat_model("custom-openai:agnes-2.5-flash", temperature=0.2)
            response = await model.ainvoke([
                {"role": "system", "content": ADVANCEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ])
            content = getattr(response, "content", "") or ""
            return _extract_json(content)
        except Exception as e:
            logger.error(f"Advancement LLM call failed: {e}")
            return {}

    async def confirm_draft(
        self, task_id: int, reviewer_id: int, edits: dict | None = None
    ) -> dict[str, Any] | None:
        """主办民警确认任务草案 → pending_confirmation → pending（待分配）。"""
        task = await task_repository.get_by_id(task_id)
        if not task or task.status != "pending_confirmation":
            return task.to_dict() if task else None
        update_data: dict[str, Any] = {"status": "pending"}
        if edits:
            for k in ("title", "description", "priority", "type", "instructions", "due_date"):
                if k in edits and edits[k] is not None:
                    update_data[k] = edits[k]
        task = await task_repository.update(task_id, update_data)
        await task_repository.create_event({
            "case_id": task.case_id,
            "task_id": task_id,
            "event_type": "reviewed",
            "event_data": {"approved": True, "reviewer_id": reviewer_id},
            "created_by": reviewer_id,
        })
        await write_audit_log(
            action="confirm_draft",
            resource_type="task",
            resource_id=task_id,
            case_id=task.case_id,
            user_id=reviewer_id,
            details={"status": "pending"},
        )
        return task.to_dict()

    async def reject_draft(
        self, task_id: int, reviewer_id: int, reason: str | None = None
    ) -> dict[str, Any] | None:
        """主办民警驳回任务草案 → pending_confirmation → cancelled。"""
        task = await task_repository.get_by_id(task_id)
        if not task or task.status != "pending_confirmation":
            return task.to_dict() if task else None
        task = await task_repository.update(
            task_id, {"status": "cancelled", "close_reason": reason or "主办民警驳回"}
        )
        await task_repository.create_event({
            "case_id": task.case_id,
            "task_id": task_id,
            "event_type": "reviewed",
            "event_data": {"approved": False, "reviewer_id": reviewer_id, "reason": reason},
            "created_by": reviewer_id,
        })
        await write_audit_log(
            action="reject_draft",
            resource_type="task",
            resource_id=task_id,
            case_id=task.case_id,
            user_id=reviewer_id,
            details={"reason": reason},
        )
        return task.to_dict()

    async def change_direction(
        self, case_id: int, new_direction: str, user_id: int
    ) -> dict[str, Any]:
        """侦查方向变更：保留已完成任务，受影响任务标注，基于新方向重新规划。

        - 已完成（completed）任务保持不变（历史记录）
        - 进行中 / 待确认 / 待开始任务不强制变更，交由主办民警在界面逐条决定
        - 基于新方向生成新的任务草案（pending_confirmation）
        - 写入决策日志与审计日志
        """
        case = await case_repository.get_by_id(case_id)
        if not case:
            return {"ok": False, "error": "case_not_found"}
        old_direction = getattr(case, "investigation_direction", None)
        await case_repository.update(case_id, {"investigation_direction": new_direction})

        affected: list[dict[str, Any]] = []
        for st in ("in_progress", "pending_confirmation", "pending"):
            tasks, _ = await task_repository.list_tasks(case_id=case_id, status=st, limit=500)
            affected.extend([t.to_dict() for t in tasks])

        new_drafts = await self._generate_drafts_from_direction(case, new_direction)
        created_ids: list[int] = []
        for d in new_drafts.get("proposed_tasks", []):
            title = (d.get("title") or "").strip()
            if not title:
                continue
            new_task = await task_repository.create({
                "case_id": case_id,
                "title": title,
                "type": d.get("type") or "investigation",
                "status": "pending_confirmation",
                "creator_type": "agent",
                "creator_id": None,
                "assignee_type": "human",
                "priority": d.get("priority") or "medium",
                "instructions": d.get("basis") or "",
                "extra": {
                    "advancement": {
                        "suggested_assignee": d.get("suggested_assignee"),
                        "direction_change": True,
                    }
                },
            })
            await task_repository.create_event({
                "case_id": case_id,
                "task_id": new_task.id,
                "event_type": "created",
                "event_data": {"auto_created": True, "creator_type": "agent", "direction_change": True},
                "created_by": None,
            })
            created_ids.append(new_task.id)

        await self._log_decision(
            case_id=case_id,
            trigger_task_id=None,
            decision_type="direction_change",
            summary=(
                f"侦查方向调整：{old_direction or '（无）'} → {new_direction}，"
                f"重新生成 {len(created_ids)} 条任务草案"
            ),
            details={
                "old_direction": old_direction,
                "new_direction": new_direction,
                "affected_task_ids": [a["id"] for a in affected],
                "generated_task_ids": created_ids,
            },
            user_id=user_id,
        )
        await write_audit_log(
            action="change_direction",
            resource_type="case",
            resource_id=case_id,
            case_id=case_id,
            user_id=user_id,
            details={"old_direction": old_direction, "new_direction": new_direction},
        )
        return {
            "ok": True,
            "old_direction": old_direction,
            "new_direction": new_direction,
            "affected_tasks": affected,
            "generated_task_ids": created_ids,
        }

    async def _generate_drafts_from_direction(self, case, direction: str) -> dict[str, Any]:
        """基于新侦查方向整体重新规划（不依赖单个完成任务）。"""
        try:
            from yuxi.agents.models import load_chat_model
        except Exception as e:  # pragma: no cover
            logger.warning(f"load_chat_model unavailable: {e}")
            return {}

        existing, _ = await task_repository.list_tasks(case_id=case.id, limit=200)
        existing_lines = [f"- [{t.status}] {t.title}（{t.type}）" for t in existing]
        existing_text = "\n".join(existing_lines) if existing_lines else "（暂无）"

        user_prompt = ADVANCEMENT_DRAFT_USER_PROMPT.format(
            case_context=_build_case_context(case),
            direction=direction,
            completed_task_title="（侦查方向调整，非单任务触发）",
            completed_task_type="direction_change",
            completed_result="（基于新侦查方向整体重新规划）",
            existing_tasks=existing_text,
        )
        try:
            model = load_chat_model("custom-openai:agnes-2.5-flash", temperature=0.2)
            response = await model.ainvoke([
                {"role": "system", "content": ADVANCEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ])
            return _extract_json(getattr(response, "content", "") or "")
        except Exception as e:
            logger.error(f"Direction change LLM failed: {e}")
            return {}

    async def _maybe_advance_phase(self, case) -> None:
        """阶段推进自检：当前阶段无进行中/待确认/待开始/审核中任务时，生成阶段小结建议。"""
        has_open = False
        for st in ("in_progress", "pending_confirmation", "pending", "review"):
            _, total = await task_repository.list_tasks(case_id=case.id, status=st, limit=1)
            if total > 0:
                has_open = True
                break
        if has_open:
            return
        await self._log_decision(
            case_id=case.id,
            trigger_task_id=None,
            decision_type="phase_summary",
            summary=(
                f"当前阶段「{case.phase or 'research'}」任务已全部完成，"
                f"建议主办民警确认并进入下一阶段"
            ),
            details={"phase": case.phase},
        )

    async def _log_decision(
        self,
        *,
        case_id: int,
        trigger_task_id: int | None,
        decision_type: str,
        summary: str | None,
        details: dict | None,
        user_id: int | None = None,
    ) -> None:
        try:
            async with pg_manager.get_async_session_context() as session:
                log = PoliceAdvancementLog(
                    case_id=case_id,
                    trigger_task_id=trigger_task_id,
                    decision_type=decision_type,
                    summary=summary,
                    details=details or {},
                    created_by=user_id,
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            logger.warning(f"Write advancement log failed: {e}")

    async def list_drafts(self, case_id: int) -> list[dict[str, Any]]:
        """列出某案件的待确认任务草案。"""
        tasks, _ = await task_repository.list_tasks(
            case_id=case_id, status="pending_confirmation", limit=500
        )
        return [t.to_dict() for t in tasks]

    async def my_drafts(self, user_id: int) -> list[dict[str, Any]]:
        """聚合当前用户参与（成员/主办）案件的待确认任务草案。

        供个人工作台「待审查」分组使用：跨案件汇总所有 pending_confirmation 任务。
        """
        try:
            cases, _ = await case_repository.list_cases(user_id=user_id, limit=500)
            case_ids = [c.id for c in cases]
            if not case_ids:
                return []
            drafts: list[dict[str, Any]] = []
            for cid in case_ids:
                tasks, _ = await task_repository.list_tasks(
                    case_id=cid, status="pending_confirmation", limit=500
                )
                drafts.extend([t.to_dict() for t in tasks])
            drafts.sort(key=lambda d: d.get("created_at") or "", reverse=True)
            return drafts
        except Exception as e:
            logger.warning(f"List my drafts failed: {e}")
            return []

    async def list_logs(self, case_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """列出某案件的推进决策日志（可解释性展示）。"""
        try:
            from sqlalchemy import select

            async with pg_manager.get_async_session_context() as session:
                result = await session.execute(
                    select(PoliceAdvancementLog)
                    .where(PoliceAdvancementLog.case_id == case_id)
                    .order_by(PoliceAdvancementLog.created_at.desc())
                    .limit(limit)
                )
                return [log.to_dict() for log in result.scalars().all()]
        except Exception as e:
            logger.warning(f"List advancement logs failed: {e}")
            return []

    async def toggle(
        self, case_id: int, enabled: bool, user_id: int
    ) -> dict[str, Any] | None:
        """启用 / 停用案件推进智能体。"""
        case = await case_repository.update(case_id, {"advancement_enabled": 1 if enabled else 0})
        if case:
            await write_audit_log(
                action="toggle_advancement",
                resource_type="case",
                resource_id=case_id,
                case_id=case_id,
                user_id=user_id,
                details={"enabled": enabled},
            )
        return case.to_dict() if case else None


police_advancement_service = PoliceAdvancementService()
