from __future__ import annotations

from io import BytesIO

from docx import Document

from yuxi.services.file_preview import (
    MAX_TEXT_PREVIEW_CHARS,
    detect_media_type,
    detect_preview_type,
    is_binary_preview_type,
    render_preview_payload,
)


def _build_docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_detect_preview_type_marks_docx_as_office_for_frontend_rendering():
    """办公文档交给前端 File Viewer 渲染，不能因 OOXML 的 ZIP 头被判成二进制。"""
    preview_type, supported, message = detect_preview_type("demo.docx", _build_docx_bytes("Docx preview"))

    assert preview_type == "office"
    assert supported is True
    assert message is None


def test_render_preview_payload_returns_docx_as_binary_office_type():
    """office 属于二进制预览类型：payload 不带文本内容，由调用方原样回传字节。"""
    payload = render_preview_payload("demo.docx", _build_docx_bytes("Docx preview text"))

    assert payload["preview_type"] == "office"
    assert payload["supported"] is True
    assert payload["content"] is None
    assert is_binary_preview_type(payload["preview_type"]) is True


def test_render_preview_payload_truncates_long_markdown():
    payload = render_preview_payload("note.md", ("x" * (MAX_TEXT_PREVIEW_CHARS + 1)).encode("utf-8"))

    assert payload["preview_type"] == "markdown"
    assert payload["supported"] is True
    assert payload["truncated"] is True
    assert payload["limit"] == MAX_TEXT_PREVIEW_CHARS
    assert len(payload["content"]) == MAX_TEXT_PREVIEW_CHARS


def test_office_preview_scope_covers_all_file_viewer_office_formats():
    """预览范围需与前端 File Viewer 支持的办公格式对齐（含 xlsx / 旧二进制 / ODF）。"""
    for name in ("a.docx", "a.doc", "a.pptx", "a.ppt", "a.xlsx", "a.xls", "a.odt", "a.ods", "a.odp"):
        preview_type, supported, _message = detect_preview_type(name, b"PK\x03\x04")
        assert (preview_type, supported) == ("office", True), name


def test_detect_media_type_returns_office_mime_for_known_extensions():
    """File Viewer 依赖响应 Content-Type 辅助判型，办公格式不能退化成 octet-stream。"""
    assert detect_media_type("a.docx", b"PK\x03\x04") == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert detect_media_type("a.xls", b"") == "application/vnd.ms-excel"
    assert detect_media_type("a.odp", b"PK\x03\x04") == "application/vnd.oasis.opendocument.presentation"
