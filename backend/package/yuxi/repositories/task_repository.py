"""★ 公安任务数据访问层"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_police import PoliceTask, TaskEvent, TaskFlowRule
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
        """列表查询 + 总数"""
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
                query = query.where(
                    PoliceTask.assignee_type == "human",
                    PoliceTask.assignee_id == my_tasks_user_id,
                    PoliceTask.status.in_(["pending", "in_progress"]),
                )
                count_query = count_query.where(
                    PoliceTask.assignee_type == "human",
                    PoliceTask.assignee_id == my_tasks_user_id,
                    PoliceTask.status.in_(["pending", "in_progress"]),
                )
            if review_user_id:
                # 待审核: status=review 且分配给该民警 或 该民警是案件成员中的 reviewer
                query = query.where(PoliceTask.status == "review")
                count_query = count_query.where(PoliceTask.status == "review")

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
                if hasattr(task, key) and value is not None:
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


task_repository = TaskRepository()
