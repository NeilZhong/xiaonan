from __future__ import annotations

from typing import Any


async def resolve_visible_knowledge_bases_for_context(context) -> list[dict[str, Any]]:
    from yuxi.knowledge.runtime import knowledge_base

    uid = getattr(context, "uid", None)
    if not uid:
        setattr(context, "_visible_knowledge_bases", [])
        return []

    result = await knowledge_base.get_databases_by_uid(str(uid))
    databases = result.get("databases") or []
    enabled_knowledges = getattr(context, "knowledges", None)
    # 安全语义：未显式配置（null 或空列表）即不关联任何知识库，避免越权访问全部知识库
    if not enabled_knowledges:
        setattr(context, "_visible_knowledge_bases", [])
        return []
    enabled_ids = {str(value).strip() for value in enabled_knowledges if str(value).strip()}
    databases = [db for db in databases if str(db.get("kb_id") or "").strip() in enabled_ids]

    setattr(context, "_visible_knowledge_bases", databases)
    return databases
