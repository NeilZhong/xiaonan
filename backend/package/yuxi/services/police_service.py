"""★ 公安业务服务层 — 案件 + 任务流转引擎"""

import hashlib
from typing import Any

from yuxi.repositories.case_repository import case_repository
from yuxi.repositories.evidence_repository import evidence_repository
from yuxi.repositories.task_repository import task_repository
from yuxi.utils.datetime_utils import utc_now_naive
from yuxi.utils import logger


class PoliceCaseService:
    """案件服务 — 编排案件创建、阶段切换、统计等业务逻辑"""

    async def create_case(self, data: dict[str, Any], creator_id: int) -> dict[str, Any]:
        """创建案件 + 自动添加创建者为 commander"""
        case = await case_repository.create(data)
        # 创建者为案件指挥员
        await case_repository.add_member(case.id, creator_id, "commander")
        # 创建初始阶段记录
        initial_phase = case.phase or "research"
        await case_repository.update_phase(case.id, initial_phase)
        # 记录审计日志
        await self._audit(action="create", resource_type="case", resource_id=case.id, case_id=case.id, user_id=creator_id, details={"title": case.title})
        return case.to_dict()

    async def get_case_detail(self, case_id: int) -> dict[str, Any] | None:
        case = await case_repository.get_by_id(case_id)
        if not case:
            return None
        result = case.to_dict()
        members = await case_repository.list_members(case_id)
        result["members"] = [m.to_dict() for m in members]
        phases = await case_repository.list_phases(case_id)
        result["phases"] = [p.to_dict() for p in phases]
        return result

    async def list_cases(self, **kwargs) -> dict[str, Any]:
        cases, total = await case_repository.list_cases(**kwargs)
        return {
            "items": [c.to_dict() for c in cases],
            "total": total,
            "page": (kwargs.get("skip", 0) // kwargs.get("limit", 20)) + 1,
            "page_size": kwargs.get("limit", 20),
        }

    async def update_case(self, case_id: int, data: dict[str, Any], user_id: int) -> dict[str, Any] | None:
        case = await case_repository.update(case_id, data)
        if case:
            await self._audit(action="update", resource_type="case", resource_id=case_id, case_id=case_id, user_id=user_id, details=data)
        return case.to_dict() if case else None

    async def delete_case(self, case_id: int, user_id: int) -> bool:
        ok = await case_repository.delete(case_id)
        if ok:
            await self._audit(action="delete", resource_type="case", resource_id=case_id, case_id=case_id, user_id=user_id)
        return ok

    async def update_phase(self, case_id: int, phase: str, user_id: int) -> dict[str, Any] | None:
        case = await case_repository.update_phase(case_id, phase)
        if case:
            await self._audit(action="phase_change", resource_type="case", resource_id=case_id, case_id=case_id, user_id=user_id, details={"phase": phase})
        return case.to_dict() if case else None

    async def add_member(self, case_id: int, user_id: int, role: str, operator_id: int) -> dict[str, Any]:
        member = await case_repository.add_member(case_id, user_id, role)
        await self._audit(action="add_member", resource_type="case", resource_id=case_id, case_id=case_id, user_id=operator_id, details={"member_user_id": user_id, "role": role})
        return member.to_dict()

    async def case_timeline(self, case_id: int) -> list[dict[str, Any]]:
        """案件时间线 — 合并任务事件和阶段记录"""
        tasks, _ = await task_repository.list_tasks(case_id=case_id, limit=1000)
        timeline = []
        for task in tasks:
            task_events = await task_repository.list_events(task.id)
            for ev in task_events:
                timeline.append({**ev.to_dict(), "task_title": task.title})
        phases = await case_repository.list_phases(case_id)
        for ph in phases:
            timeline.append({
                "event_type": "phase_change",
                "event_data": {"phase": ph.phase, "status": ph.status},
                "created_at": ph.started_at.isoformat() if ph.started_at else None,
            })
        timeline.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return timeline

    async def _audit(self, action: str, resource_type: str, resource_id: int, case_id: int | None, user_id: int, details: dict | None = None):
        """记录审计日志 (best-effort, 不阻塞主流程)"""
        try:
            from yuxi.storage.postgres.models_police import PoliceAuditLog
            from yuxi.storage.postgres.manager import pg_manager

            async with pg_manager.get_async_session_context() as session:
                log = PoliceAuditLog(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    case_id=case_id,
                    details=details,
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")


class PoliceTaskService:
    """任务服务 — 编排任务创建、分配、状态流转、自动触发规则"""

    async def create_task(self, data: dict[str, Any], creator_id: int, creator_type: str = "human") -> dict[str, Any]:
        data["creator_id"] = creator_id
        data["creator_type"] = creator_type
        task = await task_repository.create(data)
        # 记录事件
        await task_repository.create_event({
            "case_id": task.case_id,
            "task_id": task.id,
            "event_type": "created",
            "event_data": {"title": task.title, "type": task.type},
            "created_by": creator_id,
        })
        return task.to_dict()

    async def list_tasks(self, **kwargs) -> dict[str, Any]:
        tasks, total = await task_repository.list_tasks(**kwargs)
        return {
            "items": [t.to_dict() for t in tasks],
            "total": total,
            "page": (kwargs.get("skip", 0) // kwargs.get("limit", 20)) + 1,
            "page_size": kwargs.get("limit", 20),
        }

    async def get_task(self, task_id: int) -> dict[str, Any] | None:
        task = await task_repository.get_by_id(task_id)
        if not task:
            return None
        result = task.to_dict()
        events = await task_repository.list_events(task_id)
        result["events"] = [e.to_dict() for e in events]
        return result

    async def update_task(self, task_id: int, data: dict[str, Any], user_id: int) -> dict[str, Any] | None:
        task = await task_repository.update(task_id, data)
        return task.to_dict() if task else None

    async def assign_task(self, task_id: int, assignee_type: str, assignee_id: int, assignee_name: str, user_id: int) -> dict[str, Any] | None:
        task = await task_repository.assign(task_id, assignee_type, assignee_id, assignee_name)
        if task:
            await task_repository.create_event({
                "case_id": task.case_id, "task_id": task_id, "event_type": "assigned",
                "event_data": {"assignee_type": assignee_type, "assignee_id": assignee_id, "assignee_name": assignee_name},
                "created_by": user_id,
            })
        return task.to_dict() if task else None

    async def start_task(self, task_id: int, user_id: int) -> dict[str, Any] | None:
        task = await task_repository.start(task_id)
        if task:
            await task_repository.create_event({
                "case_id": task.case_id, "task_id": task_id, "event_type": "started", "event_data": {}, "created_by": user_id,
            })
        return task.to_dict() if task else None

    async def complete_task(self, task_id: int, result: dict | None, user_id: int) -> dict[str, Any] | None:
        task = await task_repository.complete(task_id, result)
        if task:
            await task_repository.create_event({
                "case_id": task.case_id, "task_id": task_id, "event_type": "completed",
                "event_data": {"result": result}, "created_by": user_id,
            })
            # ★ 触发任务流转规则
            await self._trigger_flow_rules(task)
        return task.to_dict() if task else None

    async def review_task(self, task_id: int, approved: bool, reviewer_id: int, reviewer_police_id: str) -> dict[str, Any] | None:
        """审核任务 — 通过时计算 signed_hash"""
        # 获取任务结果哈希
        task = await task_repository.get_by_id(task_id)
        if not task:
            return None
        result_str = str(task.result) if task.result else ""
        result_hash = hashlib.sha256(result_str.encode()).hexdigest()
        signed_hash = None
        if approved:
            hash_input = f"{reviewer_police_id}{utc_now_naive().isoformat()}{result_hash}"
            signed_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        task = await task_repository.review(task_id, approved, reviewer_id, signed_hash)
        if task:
            await task_repository.create_event({
                "case_id": task.case_id, "task_id": task_id, "event_type": "reviewed",
                "event_data": {"approved": approved, "reviewer_id": reviewer_id}, "created_by": reviewer_id,
            })
        return task.to_dict() if task else None

    async def _trigger_flow_rules(self, task) -> None:
        """★ 任务流转规则引擎 — 根据已完成任务自动创建后续任务"""
        try:
            rules = await task_repository.list_flow_rules(task.case_id)
            for rule in rules:
                if rule.trigger_event != "task_completed":
                    continue
                # 简单条件匹配: condition.task_type == task.type
                condition = rule.condition or {}
                if condition.get("task_type") and condition["task_type"] != task.type:
                    continue
                if rule.action == "create_task":
                    # 检查 result 中是否有下一级账户等数据
                    result = task.result or {}
                    next_accounts = result.get("next_level_accounts", [])
                    if condition.get("has_next_level") and not next_accounts:
                        continue
                    new_task_data = {
                        "case_id": task.case_id,
                        "title": f"{rule.target_task_type} — 自动生成",
                        "type": rule.target_task_type,
                        "status": "pending",
                        "assignee_type": rule.target_assignee_type or "agent",
                        "assignee_id": rule.target_assignee_id,
                        "priority": task.priority,
                        "phase": task.phase,
                        "parent_task_id": task.id,
                        "instructions": f"由任务「{task.title}」完成后自动创建。关联数据: {next_accounts}",
                    }
                    new_task = await task_repository.create(new_task_data)
                    await task_repository.create_event({
                        "case_id": task.case_id, "task_id": new_task.id, "event_type": "created",
                        "event_data": {"auto_created": True, "parent_task_id": task.id, "rule_id": rule.id},
                        "created_by": None,
                    })
                    logger.info(f"Flow rule triggered: created task {new_task.id} from task {task.id}")
        except Exception as e:
            logger.warning(f"Flow rule trigger failed: {e}")


class PoliceDashboardService:
    """工作台统计服务"""

    async def get_stats(self, user_id: int) -> dict[str, Any]:
        """工作台统计数据"""
        my_tasks, my_count = await task_repository.list_tasks(my_tasks_user_id=user_id, limit=1000)
        review_tasks, review_count = await task_repository.list_tasks(review_user_id=user_id, limit=1000)
        in_progress = [t for t in my_tasks if t.status == "in_progress"]
        pending = [t for t in my_tasks if t.status == "pending"]
        return {
            "my_pending_count": len(pending),
            "my_in_progress_count": len(in_progress),
            "review_count": review_count,
            "my_tasks_total": my_count,
        }

    async def get_my_tasks(self, user_id: int, skip: int = 0, limit: int = 20) -> dict[str, Any]:
        tasks, total = await task_repository.list_tasks(my_tasks_user_id=user_id, skip=skip, limit=limit)
        return {"items": [t.to_dict() for t in tasks], "total": total}

    async def get_review_tasks(self, user_id: int, skip: int = 0, limit: int = 20) -> dict[str, Any]:
        tasks, total = await task_repository.list_tasks(review_user_id=user_id, skip=skip, limit=limit)
        return {"items": [t.to_dict() for t in tasks], "total": total}


police_case_service = PoliceCaseService()
police_task_service = PoliceTaskService()
police_dashboard_service = PoliceDashboardService()
