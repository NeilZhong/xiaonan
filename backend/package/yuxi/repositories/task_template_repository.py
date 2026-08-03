"""★ 侦查任务模板数据访问层

对应 police_task_templates 表，为推进智能体提供「要素 → 任务」的映射规则。
"""

from typing import Any

from sqlalchemy import select

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_police import PoliceTaskTemplate

# 允许外部写入的字段白名单（防止越权改 id / created_at 等）
WRITABLE_FIELDS = (
    "code",
    "name",
    "description",
    "element_type",
    "case_types",
    "phases",
    "source_task_types",
    "task_title",
    "task_type",
    "task_description",
    "instructions",
    "priority",
    "suggested_agent_type",
    "due_days",
    "next_template_codes",
    "enabled",
    "sort_order",
)


class TaskTemplateRepository:
    """侦查任务模板数据访问层"""

    async def list_templates(
        self,
        element_type: str | None = None,
        enabled_only: bool = False,
        keyword: str | None = None,
    ) -> list[PoliceTaskTemplate]:
        async with pg_manager.get_async_session_context() as session:
            query = select(PoliceTaskTemplate)
            if element_type:
                query = query.where(PoliceTaskTemplate.element_type == element_type)
            if enabled_only:
                query = query.where(PoliceTaskTemplate.enabled == 1)
            if keyword:
                pattern = f"%{keyword}%"
                query = query.where(PoliceTaskTemplate.name.ilike(pattern))
            query = query.order_by(
                PoliceTaskTemplate.sort_order.asc(), PoliceTaskTemplate.id.asc()
            )
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_by_id(self, template_id: int) -> PoliceTaskTemplate | None:
        async with pg_manager.get_async_session_context() as session:
            return await session.get(PoliceTaskTemplate, template_id)

    async def get_by_code(self, code: str) -> PoliceTaskTemplate | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(PoliceTaskTemplate).where(PoliceTaskTemplate.code == code)
            )
            return result.scalar_one_or_none()

    async def get_by_codes(self, codes: list[str]) -> list[PoliceTaskTemplate]:
        """批量按 code 取模板（链式推进用）。"""
        if not codes:
            return []
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(PoliceTaskTemplate).where(PoliceTaskTemplate.code.in_(codes))
            )
            return list(result.scalars().all())

    async def create(self, data: dict[str, Any]) -> PoliceTaskTemplate:
        payload = {k: v for k, v in data.items() if k in WRITABLE_FIELDS or k in ("is_builtin", "created_by")}
        async with pg_manager.get_async_session_context() as session:
            template = PoliceTaskTemplate(**payload)
            session.add(template)
            await session.commit()
            await session.refresh(template)
            return template

    async def update(self, template_id: int, data: dict[str, Any]) -> PoliceTaskTemplate | None:
        async with pg_manager.get_async_session_context() as session:
            template = await session.get(PoliceTaskTemplate, template_id)
            if not template:
                return None
            for key, value in data.items():
                # 允许显式置空（如清掉 due_days / element_type），故不过滤 None
                if key in WRITABLE_FIELDS:
                    setattr(template, key, value)
            await session.commit()
            await session.refresh(template)
            return template

    async def delete(self, template_id: int) -> bool:
        async with pg_manager.get_async_session_context() as session:
            template = await session.get(PoliceTaskTemplate, template_id)
            if not template:
                return False
            await session.delete(template)
            await session.commit()
            return True

    async def upsert_by_code(self, code: str, data: dict[str, Any]) -> PoliceTaskTemplate:
        """按 code 幂等写入（内置模板植入用）。

        已存在时**只补齐缺失字段**，不覆盖民警已经改过的内容 —— 避免每次重启把
        本单位定制的模板刷回出厂设置。
        """
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(PoliceTaskTemplate).where(PoliceTaskTemplate.code == code)
            )
            template = result.scalar_one_or_none()
            if template:
                changed = False
                for key, value in data.items():
                    if key in WRITABLE_FIELDS and getattr(template, key, None) in (None, "", [], {}):
                        setattr(template, key, value)
                        changed = True
                if template.is_builtin != 1:
                    template.is_builtin = 1
                    changed = True
                if changed:
                    await session.commit()
                    await session.refresh(template)
                return template
            payload = {k: v for k, v in data.items() if k in WRITABLE_FIELDS}
            payload["code"] = code
            payload["is_builtin"] = 1
            template = PoliceTaskTemplate(**payload)
            session.add(template)
            await session.commit()
            await session.refresh(template)
            return template

    async def count(self) -> int:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(PoliceTaskTemplate.id))
            return len(list(result.scalars().all()))


task_template_repository = TaskTemplateRepository()
