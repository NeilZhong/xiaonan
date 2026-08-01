"""★ 笔录分析服务 — 从讯问/询问笔录提取结构化案件信息。

复用 Yuxi 既有能力，不重复造轮子：
- 文本/Office 类文件直接按 UTF-8 读取；PDF/图片类走 ``ocr_service.parse_document``
  （统一 OCR 网关，内部完成引擎选择与配置解析）。
- LLM 调用走 ``agents.models.load_chat_model``（OpenAI 兼容，默认 agnes）。
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from yuxi.agents.models import load_chat_model
from yuxi.services.ocr_service import parse_document
from yuxi.utils.logging_config import logger

# 直接当作文本读取的扩展名（无需 OCR）
_TEXT_EXTENSIONS = {
    ".txt",
    ".text",
    ".md",
    ".markdown",
    ".csv",
    ".log",
    ".json",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
    ".xml",
}
# 需要 OCR 解析的扩展名
_OCR_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".tif",
    ".gif",
    ".webp",
}

# 笔录分析 Prompt：要求模型只输出结构化 JSON
_ANALYSIS_SYSTEM_PROMPT = """你是一名资深刑侦民警助手，擅长从笔录中快速提取结构化案件信息。
请阅读下面给出的讯问/询问笔录原文，提取案件要素，并严格只输出一个 JSON 对象
（不要使用 markdown 代码块、不要输出任何解释性文字），结构如下：

{
  "case_overview": {
    "title": "案件标题，简洁概括，如『张某被诈骗案』",
    "case_type": "案件类型枚举之一：fraud(诈骗)/theft(盗窃)/drug(毒品)/economic(经济犯罪)/other(其他)",
    "incident_date": "案发时间（原文表述或推断，字符串，无法确定填空字符串）",
    "incident_location": "案发地点（无法确定填空字符串）",
    "priority": "紧急程度枚举之一：low/medium/high/urgent",
    "total_amount": "涉案金额（数字，无则填 null）",
    "victim": { "name": "受害人姓名或称谓", "role": "身份，如『被害人』" },
    "suspects": [ { "name": "嫌疑人姓名或称谓", "role": "身份" } ],
    "summary": "案件概述，2-4 句话，客观陈述已掌握事实",
    "key_facts": ["关键事实1", "关键事实2"]
  },
  "suggested_tasks": [
    {
      "title": "任务标题",
      "type": "任务类型，如：笔录分析/证据收集/嫌疑人核查/资金流向分析/现场勘验/伤情鉴定",
      "priority": "low/medium/high/urgent",
      "description": "任务说明与目的",
      "assignee_type": "human"
    }
  ]
}

要求：
- 信息缺失时填空字符串或 null，不要编造。
- suggested_tasks 至少给出 3 条贴合本案的后续侦办任务。
- 只输出 JSON。"""


async def extract_text(*, file_bytes: bytes, filename: str, db: Any = None) -> str:
    """从上传的笔录文件提取纯文本。

    - 文本类扩展名：按 UTF-8 直读。
    - PDF/图片类：落临时文件后交 ``ocr_service.parse_document``（统一 OCR 网关）。
    - 不支持的类型直接抛 ``ValueError``。
    """
    suffix = Path(filename).suffix.lower()
    if suffix in _TEXT_EXTENSIONS:
        return file_bytes.decode("utf-8", errors="replace")

    if suffix in _OCR_EXTENSIONS:
        if db is None:
            raise ValueError("OCR 解析需要数据库会话")
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            # 业务唯一文档解析入口，内部完成引擎选择与配置解析
            return await parse_document(tmp_path, db=db)
        except Exception as e:
            logger.warning(f"笔录 OCR 解析失败: {e}")
            raise ValueError(
                f"笔录 OCR 解析失败（请确认 OCR 服务已启动，或改用文本上传）: {e}"
            ) from e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    raise ValueError(f"不支持的笔录文件类型: {suffix or '未知'}，仅支持 txt/md/pdf/png/jpg 等")


def _safe_parse_json(content: str) -> dict:
    """从 LLM 输出中容错提取 JSON 对象。"""
    content = content.strip()
    # 去掉可能的 ```json ... ``` 包裹
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    # 提取首个 { 到末个 } 之间的内容
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            pass
    # 兜底：容错修复，处理 LLM 常见的未转义内嵌引号、尾随逗号等问题
    try:
        from json_repair import repair_json

        repaired = repair_json(content, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
    except Exception:
        pass
    raise ValueError("AI 返回内容不是合法 JSON，请重试或检查模型配置")


_MAX_TRANSCRIPT_CHARS = 30000


async def analyze_transcript(raw_text: str, model: str | None = None) -> dict:
    """调用 LLM 将笔录原文结构化，返回案件概览 + 建议任务草稿。

    Args:
        raw_text: 笔录纯文本（建议不超过 3 万字）。
        model: 可选模型 spec，缺省走系统默认模型（agnes）。

    Returns:
        dict: ``{"case_overview": {...}, "suggested_tasks": [...]}``
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("笔录内容为空")
    if len(raw_text) > _MAX_TRANSCRIPT_CHARS:
        logger.warning(f"笔录过长({len(raw_text)}字)，截断至 {_MAX_TRANSCRIPT_CHARS}")
        raw_text = raw_text[:_MAX_TRANSCRIPT_CHARS]

    chat_model = load_chat_model(model)
    messages = [
        SystemMessage(content=_ANALYSIS_SYSTEM_PROMPT),
        HumanMessage(content=f"以下是笔录原文：\n\n{raw_text}"),
    ]
    resp = await chat_model.ainvoke(messages)
    content = resp.content if isinstance(resp.content, str) else str(resp.content)
    data = _safe_parse_json(content)

    overview = data.get("case_overview") or {}
    tasks = data.get("suggested_tasks") or []
    if not isinstance(tasks, list):
        tasks = []
    return {"case_overview": overview, "suggested_tasks": tasks}
