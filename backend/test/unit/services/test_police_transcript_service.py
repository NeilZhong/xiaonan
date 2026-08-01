"""笔录分析服务单元测试 — 不依赖真实 LLM / OCR 服务 / 数据库。"""

import json

import pytest

from yuxi.services import police_transcript_service as svc


class _FakeAIMessage:
    def __init__(self, content):
        self.content = content


class _FakeModel:
    """模拟 load_chat_model 返回的聊天模型，直接回吐给定 content。"""

    def __init__(self, content):
        self._content = content

    async def ainvoke(self, messages):
        return _FakeAIMessage(self._content)


_PAYLOAD = {
    "case_overview": {
        "title": "张某被诈骗案",
        "case_type": "fraud",
        "incident_date": "2026-03-12",
        "incident_location": "某市某区",
        "priority": "high",
        "total_amount": 50000,
        "victim": {"name": "张某", "role": "被害人"},
        "suspects": [{"name": "李某", "role": "嫌疑人"}],
        "summary": "张某遭电信网络诈骗。",
        "key_facts": ["通过冒充客服实施诈骗", "转账 5 万元"],
    },
    "suggested_tasks": [
        {"title": "资金流向分析", "type": "资金流向分析", "priority": "high", "description": "追查资金链路", "assignee_type": "human"},
    ],
}


async def test_extract_text_plain(monkeypatch):
    result = await svc.extract_text(file_bytes=b"hello world", filename="a.txt")
    assert result == "hello world"


async def test_extract_text_unsupported_type(monkeypatch):
    with pytest.raises(ValueError):
        await svc.extract_text(file_bytes=b"x", filename="a.xyz")


async def test_extract_text_ocr_requires_db(monkeypatch):
    # OCR 类型但未提供 db 会话，应明确报错而非尝试连接
    with pytest.raises(ValueError):
        await svc.extract_text(file_bytes=b"%PDF-1.4", filename="a.pdf", db=None)


async def test_analyze_transcript_parses_json(monkeypatch):
    monkeypatch.setattr(svc, "load_chat_model", lambda model: _FakeModel(json.dumps(_PAYLOAD)))
    draft = await svc.analyze_transcript("这是一段笔录原文", model=None)
    assert draft["case_overview"]["title"] == "张某被诈骗案"
    assert draft["suggested_tasks"][0]["title"] == "资金流向分析"


async def test_analyze_transcript_empty(monkeypatch):
    with pytest.raises(ValueError):
        await svc.analyze_transcript("   ", model=None)


async def test_analyze_transcript_codeblock_wrapped(monkeypatch):
    # 模型偶尔会用 ```json 包裹，需容错提取
    wrapped = "```json\n" + json.dumps(_PAYLOAD) + "\n```"
    monkeypatch.setattr(svc, "load_chat_model", lambda model: _FakeModel(wrapped))
    draft = await svc.analyze_transcript("笔录", model=None)
    assert draft["case_overview"]["title"] == "张某被诈骗案"
    assert draft["suggested_tasks"][0]["title"] == "资金流向分析"
