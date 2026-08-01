"""★ 笔录导入 API — 上传笔录 → AI 分析 → 民警确认 → 建案并生成初始任务。

设计要点：
- ``/transcript`` 只负责「分析生成草稿」，不落库，符合「智能体产出需民警确认」的审批约束。
- ``/transcript/confirm`` 才复用 ``police_case_service`` / ``police_task_service`` 落库，
  自动走既有审计埋点，避免重复造轮子。
"""

from __future__ import annotations

import datetime
import random
import re
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user
from yuxi.services.police_service import police_case_service, police_task_service
from yuxi.services.police_transcript_service import analyze_transcript, extract_text
from yuxi.storage.postgres.models_business import User

import_router = APIRouter(prefix="/police/import", tags=["police-import"])


# ── 请求 Schema ──────────────────────────────────────────────
class TaskDraft(BaseModel):
    title: str
    type: str | None = None
    priority: str = "medium"
    description: str | None = None
    assignee_type: str = "human"


class CaseOverviewDraft(BaseModel):
    title: str = ""
    case_type: str | None = None
    incident_date: str | None = None
    incident_location: str | None = None
    priority: str = "medium"
    total_amount: float | None = None
    victim: dict | None = None
    suspects: list | None = None
    summary: str | None = None
    key_facts: list | None = None


class ConfirmBody(BaseModel):
    overview: CaseOverviewDraft
    tasks: list[TaskDraft] = []
    description: str | None = None  # 允许覆盖案件描述


def _gen_case_number() -> str:
    """生成导入案件的临时编号（避免与手工编号冲突）。"""
    return f"TR{datetime.datetime.now().strftime('%Y%m%d')}{random.randint(100, 999)}"


def _coerce_incident_date(value: Any) -> tuple[datetime.datetime | None, str | None]:
    """把 AI 给出的案发时间（自由文本）尽量解析为 datetime。

    解析失败时返回 ``(None, 原文)``，由调用方把原文保留进 ``extra`` 不丢信息；
    ``police_cases.incident_date`` 为 DateTime 列，不允许直接写入自然语言字符串。
    """
    if value is None or not str(value).strip():
        return None, None
    if isinstance(value, datetime.datetime):
        return value, None
    if isinstance(value, datetime.date):
        return datetime.datetime(value.year, value.month, value.day), None

    s = str(value).strip()
    # ISO 8601（含纯日期 YYYY-MM-DD）
    try:
        cleaned = s.replace("Z", "").strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?", cleaned):
            return datetime.datetime.fromisoformat(cleaned), None
    except ValueError:
        pass
    # 中文：2026年3月10日（晚）/ 2026年3月10日14时
    m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?", s)
    if m:
        try:
            return datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))), None
        except ValueError:
            pass
    return None, s


@import_router.post("/transcript")
async def import_transcript(
    file: UploadFile | None = File(None),
    text: str = Form(""),
    model: str | None = Form(None),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """上传笔录（文件或粘贴文本）→ AI 结构化分析 → 返回案件概览 + 建议任务草稿。"""
    raw_text = text or ""
    if file is not None:
        content = await file.read()
        raw_text = await extract_text(
            file_bytes=content, filename=file.filename or "transcript.txt", db=db
        )
    elif not raw_text.strip():
        raise HTTPException(status_code=400, detail="请上传笔录文件或粘贴笔录文本")

    draft = await analyze_transcript(raw_text, model)
    return {"code": 0, "message": "success", "data": draft}


@import_router.post("/transcript/confirm")
async def confirm_import(
    body: ConfirmBody,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """确认建案：用 AI 草稿创建案件并批量生成初始任务。"""
    ov = body.overview
    incident_date, incident_date_original = _coerce_incident_date(ov.incident_date)
    extra: dict[str, Any] = {"key_facts": ov.key_facts, "imported_from": "transcript"}
    if incident_date_original is not None:
        extra["incident_date_original"] = incident_date_original

    case_data: dict[str, Any] = {
        "case_number": _gen_case_number(),
        "title": ov.title or "未命名案件",
        "case_type": ov.case_type,
        "description": body.description or ov.summary,
        "priority": ov.priority or "medium",
        "incident_date": incident_date,
        "incident_location": ov.incident_location,
        "total_amount": ov.total_amount,
        "victim_info": ov.victim,
        "suspect_info": ov.suspects,
        "extra": extra,
    }
    case = await police_case_service.create_case(case_data, current_user.id)
    case_id = case["id"]

    task_ids: list[int] = []
    for t in body.tasks:
        created = await police_task_service.create_task(
            {
                "case_id": case_id,
                "title": t.title,
                "type": t.type or "other",
                "priority": t.priority or "medium",
                "description": t.description,
                "assignee_type": t.assignee_type or "human",
            },
            creator_id=current_user.id,
            creator_type="agent",
        )
        task_ids.append(created["id"])

    return {
        "code": 0,
        "message": "success",
        "data": {"case_id": case_id, "task_ids": task_ids},
    }
