"""★ 公安任务数据访问层"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_police import PoliceTask, TaskAssignee, TaskEvent, TaskFlowRule
from yuxi.utils.datetime_utils import utc_now_naive


class TaskRepository:
    """公安任务数据访问层"""

    async def get_by_id(self, task_id: int) -> PoliceTask | None:
        async with pg_manager.get_async_session_context() as session:
            return await session.get(PoliceTask, task_id)

    async def list_all(self) -> list[PoliceTask]:
        """返回全部任务记录（task_service 启动时恢复内存队列状态用）"""
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(PoliceTask))
            return list(result.scalars().all())

    async def list_tasks(
        self,
        skip: int = 0,
        limit: int = 20,
        case_id: int | None = None,
        status: str | None = None,
        assignee_type: str | None = None,
        assignee_id: int | None = None,
        task_type: str | None = None,
        keyword: str | None = None,
        my_tasks_user_id: int | None = None,
        review_user_id: int | None = None,
    ) -> tuple[list[PoliceTask], int]:
        """列表查询 + 总数（支持多执行人 JOIN 查询）"""
        async with pg_manager.get_async_session_context() as session:
            query = select(PoliceTask)
            count_query = select(func.count(PoliceTask.id))

            if case_id:
                query = query.where(PoliceTask.case_id == case_id)
                count_query = count_query.where(PoliceTask.case_id == case_id)
            if status:
                query = query.where(PoliceTask.status == status)
                count_query = count_query.where(PoliceTask.status == status)
            if assignee_type:
                query = query.where(PoliceTask.assignee_type == assignee_type)
                count_query = count_query.where(PoliceTask.assignee_type == assignee_type)
            if assignee_id:
                query = query.where(PoliceTask.assignee_id == assignee_id)
                count_query = count_query.where(PoliceTask.assignee_id == assignee_id)
            if task_type:
                query = query.where(PoliceTask.type == task_type)
                count_query = count_query.where(PoliceTask.type == task_type)
            if keyword:
                pattern = f"%{keyword}%"
                query = query.where(PoliceTask.title.ilike(pattern))
                count_query = count_query.where(PoliceTask.title.ilike(pattern))
            if my_tasks_user_id:
                # 通过 TaskAssignee 关联表查找：当前用户作为执行人的待办/进行中任务
                query = query.join(TaskAssignee, PoliceTask.id == TaskAssignee.task_id).where(
                    TaskAssignee.assignee_type == "human",
                    TaskAssignee.assignee_id == my_tasks_user_id,
                    PoliceTask.status.in_(["pending", "in_progress"]),
                )
                count_query = count_query.join(TaskAssignee, PoliceTask.id == TaskAssignee.task_id).where(
                    TaskAssignee.assignee_type == "human",
                    TaskAssignee.assignee_id == my_tasks_user_id,
                    PoliceTask.status.in_(["pending", "in_progress"]),
                )
            if review_user_id:
                # 待审核任务：status=review 且
                #   (a) 当前用户是任务的执行人之一，或
                #   (b) 当前用户是案件指挥员(commander)
                from yuxi.storage.postgres.models_police import CaseMember
                review_subquery = select(PoliceTask.id).join(
                    TaskAssignee, PoliceTask.id == TaskAssignee.task_id
                ).where(
                    TaskAssignee.assignee_type == "human",
                    TaskAssignee.assignee_id == review_user_id,
                ).union_all(
                    select(PoliceTask.id).join(
                        CaseMember, PoliceTask.case_id == CaseMember.case_id
                    ).where(
                        CaseMember.user_id == review_user_id,
                        CaseMember.role == "commander",
                    )
                )
                query = query.where(
                    PoliceTask.status == "review",
                    PoliceTask.id.in_(review_subquery),
                )
                count_query = count_query.where(
                    PoliceTask.status == "review",
                    PoliceTask.id.in_(review_subquery),
                )

            query = query.order_by(PoliceTask.priority.desc(), PoliceTask.created_at.desc()).offset(skip).limit(limit)
            result = await session.execute(query)
            tasks = list(result.scalars().all())
            count_result = await session.execute(count_query)
            total = count_result.scalar() or 0
            return tasks, total

    async def create(self, data: dict[str, Any]) -> PoliceTask:
        async with pg_manager.get_async_session_context() as session:
            task = PoliceTask(**data)
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task

    async def update(self, task_id: int, data: dict[str, Any]) -> PoliceTask | None:
        async with pg_manager.get_async_session_context() as session:
            task = await session.get(PoliceTask, task_id)
            if not task:
                return None
            for key, value in data.items():
                if hasattr(task, key):
                    # completed_at 允许显式置空（看板拖出「已完成」时需清空）
                    if value is None and key != "completed_at":
                        continue
                    setattr(task, key, value)
            await session.commit()
            await session.refresh(task)
            return task

    async def upsert(self, task_id: int, data: dict[str, Any]) -> PoliceTask:
        """按 id 更新或插入任务（task_service 持久化 LangGraph 状态时调用）。"""
        async with pg_manager.get_async_session_context() as session:
            task = await session.get(PoliceTask, task_id)
            if task:
                for key, value in data.items():
                    if hasattr(task, key) and value is not None:
                        setattr(task, key, value)
            else:
                payload = {k: v for k, v in data.items() if v is not None}
                payload["id"] = task_id
                task = PoliceTask(**payload)
                session.add(task)
            await session.commit()
            await session.refresh(task)
            return task

    async def assign(self, task_id: int, assignee_type: str, assignee_id: int, assignee_name: str) -> PoliceTask | None:
        """向后兼容的单执行人分配（同步更新冗余字段）"""
        async with pg_manager.get_async_session_context() as session:
            task = await session.get(PoliceTask, task_id)
            if not task:
                return None
            task.assignee_type = assignee_type
            task.assignee_id = assignee_id
            task.assignee_name = assignee_name
            await session.commit()
            await session.refresh(task)
            return task

    async def start(self, task_id: int) -> PoliceTask | None:
        async with pg_manager.get_async_session_context() as session:
            task = await session.get(PoliceTask, task_id)
            if not task:
                return None
            task.status = "in_progress"
            task.started_at = utc_now_naive()
            await session.commit()
            await session.refresh(task)
            return task

    async def complete(self, task_id: int, result: dict | None = None) -> PoliceTask | None:
        async with pg_manager.get_async_session_context() as session:
            task = await session.get(PoliceTask, task_id)
            if not task:
                return None
            task.status = "review"
            task.completed_at = utc_now_naive()
            if result:
                task.result = result
            await session.commit()
            await session.refresh(task)
            return task

    async def review(
        self, task_id: int, approved: bool, reviewer_id: int, signed_hash: str | None = None
    ) -> PoliceTask | None:
        """审核任务: approved=True→completed, False→blocked"""
        async with pg_manager.get_async_session_context() as session:
            task = await session.get(PoliceTask, task_id)
            if not task:
                return None
            if approved:
                task.status = "completed"
                task.reviewed_by = reviewer_id
                task.reviewed_at = utc_now_naive()
                task.signed_hash = signed_hash
            else:
                task.status = "blocked"
            await session.commit()
            await session.refresh(task)
            return task

    # ── 任务事件 ──────────────────────────────────────────────

    async def create_event(self, event_data: dict[str, Any]) -> TaskEvent:
        async with pg_manager.get_async_session_context() as session:
            event = TaskEvent(**event_data)
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event

    async def list_events(self, task_id: int) -> list[TaskEvent]:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(TaskEvent).where(TaskEvent.task_id == task_id).order_by(TaskEvent.created_at)
            )
            return list(result.scalars().all())

    # ── 流转规则 ──────────────────────────────────────────────

    async def list_flow_rules(self, case_id: int | None = None) -> list[TaskFlowRule]:
        async with pg_manager.get_async_session_context() as session:
            query = select(TaskFlowRule).where(TaskFlowRule.enabled == 1)
            if case_id:
                query = query.where((TaskFlowRule.case_id == case_id) | (TaskFlowRule.case_id.is_(None)))
            result = await session.execute(query)
            return list(result.scalars().all())

    async def create_flow_rule(self, data: dict[str, Any]) -> TaskFlowRule:
        """创建任务流转规则 (POLICE_REQUIREMENTS §3.4 / §6 自动流转)"""
        async with pg_manager.get_async_session_context() as session:
            rule = TaskFlowRule(**data)
            session.add(rule)
            await session.commit()
            await session.refresh(rule)
            return rule

    async def delete_flow_rule(self, rule_id: int) -> bool:
        async with pg_manager.get_async_session_context() as session:
            rule = await session.get(TaskFlowRule, rule_id)
            if not rule:
                return False
            await session.delete(rule)
            await session.commit()
            return True

    # ── 多执行人管理 (TaskAssignee) ──────────────────────────

    async def get_assignees(self, task_id: int) -> list[TaskAssignee]:
        """获取任务的全部执行人列表"""
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(TaskAssignee).where(TaskAssignee.task_id == task_id)
                    .order_by(TaskAssignee.assignee_type, TaskAssignee.id)
            )
            return list(result.scalars().all())

    async def set_assignees(self, task_id: int, assignees: list[dict]) -> list[TaskAssignee]:
        """替换任务的全部执行人（先删后插），返回新列表。

        assignees 每项格式: {assignee_type, assignee_id, assignee_name, role?}
        """
        async with pg_manager.get_async_session_context() as session:
            old = await session.execute(
                select(TaskAssignee).where(TaskAssignee.task_id == task_id)
            )
            for row in old.scalars().all():
                await session.delete(row)
            new_list = []
            for a in assignees:
                ta = TaskAssignee(
                    task_id=task_id,
                    assignee_type=a["assignee_type"],
                    assignee_id=a.get("assignee_id"),
                    assignee_name=a.get("assignee_name", ""),
                    role=a.get("role", "executor"),
                )
                session.add(ta)
                new_list.append(ta)
            await session.commit()
            for ta in new_list:
                await session.refresh(ta)
            return new_list

    async def get_task_with_assignees(self, task_id: int) -> PoliceTask | None:
        """获取任务详情（预加载执行人列表）"""
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(PoliceTask).options(selectinload(PoliceTask.assignees))
                    .where(PoliceTask.id == task_id)
            )
            return result.scalar_one_or_none()

    async def get_assignee_summary(self, task_id: int) -> dict[str, Any]:
        """返回任务执行人摘要：{humans, agents, has_human, has_agent}"""
        assignees = await self.get_assignees(task_id)
        humans = [a.to_dict() for a in assignees if a.assignee_type == "human"]
        agents = [a.to_dict() for a in assignees if a.assignee_type == "agent"]
        return {
            "humans": humans, "agents": agents,
            "has_human": len(humans) > 0, "has_agent": len(agents) > 0,
            "total": len(assignees),
        }

    # ── 审核人解析 (v2.1 §4.3 / §9.2) ────────────────────────

    async def get_commander_id(self, case_id: int) -> int | None:
        """返回案件指挥员(commander)的 users.id"""
        async with pg_manager.get_async_session_context() as session:
            from yuxi.storage.postgres.models_police import CaseMember

            result = await session.execute(
                select(CaseMember.user_id).where(
                    CaseMember.case_id == case_id, CaseMember.role == "commander"
                )
            )
            return result.scalar_one_or_none()

    async def resolve_reviewer(self, task_id: int) -> tuple[int | None, int]:
        """按 v2.1 §4.3 规则解算审核人，返回 (reviewer_id, require_approval)。

        规则：
          - 任务分配给「用户 + 数字警察」(both) → 审核人 = 指定的首个人类执行人
          - 任务仅分配给「数字警察」(agent)   → 审核人 = 案件指挥员(commander)
          - 任务仅分配给「用户」(user)        → 无需审核 (require_approval=0)
        向后兼容：无 TaskAssignee 时退回 PoliceTask 冗余字段 assignee_type/assignee_id。
        """
        task = await self.get_task_with_assignees(task_id)
        if not task:
            return None, 0
        assignees = task.assignees or []
        if assignees:
            humans = [a.assignee_id for a in assignees
                      if a.assignee_type == "human" and (a.role or "executor") == "executor"]
            agents = [a for a in assignees if a.assignee_type == "agent"]
        else:
            humans = [task.assignee_id] if task.assignee_type == "human" else []
            agents = [task.assignee_id] if task.assignee_type == "agent" else []

        if humans and agents:
            return humans[0], 1
        if agents and not humans:
            commander_id = await self.get_commander_id(task.case_id)
            return commander_id, 1
        return None, 0

    async def set_reviewer(self, task_id: int, reviewer_id: int | None, require_approval: int) -> None:
        """落盘审核人解算结果（幂等，仅当列存在时写入）"""
        async with pg_manager.get_async_session_context() as session:
            task = await session.get(PoliceTask, task_id)
            if not task:
                return
            task.reviewer_id = reviewer_id
            task.require_approval = require_approval
            await session.commit()


task_repository = TaskRepository()
