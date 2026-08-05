"""★ 异步任务队列(Tasker) 专用数据访问层。

历史背景：
原 yuxi 的 `Tasker`(后台异步任务队列) 持久化到独立的 `tasks` 表(模型
`TaskRecord`, 主键为 32 位十六进制字符串 uuid)。公安 Fork 阶段将
`task_repository.py` 整体改为指向业务任务表 `PoliceTask`(整数自增主键)，
导致 `Tasker` 把字符串 id 传入 `session.get(PoliceTask, ...)` 时触发
asyncpg 类型错误 (str 无法转 int)，后台任务(知识库入库、RAG 评估等)全部无法落库。

此文件恢复 Tasker 对 `tasks` 表的独立持久化，与业务任务表 `PoliceTask`
解耦，避免两类任务共用同一主键类型造成的冲突。
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_business import TaskRecord


class TaskerTaskRepository:
    """异步任务队列(Tasker) 数据访问层 —— 操作 `tasks` 表 (TaskRecord)。"""

    async def get_by_id(self, task_id: str) -> TaskRecord | None:
        async with pg_manager.get_async_session_context() as session:
            return await session.get(TaskRecord, task_id)

    async def list_all(self) -> list[TaskRecord]:
        """返回全部任务记录（task_service 启动时恢复内存队列状态用）"""
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(TaskRecord))
            return list(result.scalars().all())

    async def upsert(self, task_id: str, data: dict[str, Any]) -> TaskRecord:
        """按 id 更新或插入任务（task_service 持久化任务状态时调用）。

        task_id 为 32 位十六进制字符串 (uuid4().hex)，对应 TaskRecord.id(String(32))。
        """
        async with pg_manager.get_async_session_context() as session:
            task = await session.get(TaskRecord, task_id)
            if task:
                for key, value in data.items():
                    if hasattr(task, key) and value is not None:
                        setattr(task, key, value)
            else:
                payload = {k: v for k, v in data.items() if v is not None}
                payload["id"] = task_id
                task = TaskRecord(**payload)
                session.add(task)
            await session.commit()
            await session.refresh(task)
            return task

    async def delete(self, task_id: str) -> None:
        async with pg_manager.get_async_session_context() as session:
            task = await session.get(TaskRecord, task_id)
            if task:
                await session.delete(task)
                await session.commit()


tasker_task_repository = TaskerTaskRepository()
