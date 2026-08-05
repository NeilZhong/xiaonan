from __future__ import annotations

import mimetypes
from pathlib import PurePosixPath

MAX_BINARY_PREVIEW_SIZE_BYTES = 30 * 1024 * 1024
MAX_TEXT_PREVIEW_CHARS = 250_000

_MARKDOWN_EXTENSIONS = frozenset({".md", ".markdown", ".mdx"})
_PDF_EXTENSIONS = frozenset({".pdf"})
_HTML_EXTENSIONS = frozenset({".html", ".htm"})
# 办公文档统一由前端 File Viewer 渲染，后端只负责原样吐字节，不再做 PDF 转换。
# 该集合需与前端 web/src/utils/file_preview.js 的 OFFICE_EXTENSIONS 保持一致。
_OFFICE_EXTENSIONS = frozenset(
    {".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".odt", ".ods", ".odp"}
)
# preset-engineering 覆盖的格式（XMind / CAD / 3D / 压缩包 / PSD / Geo / Typst / EDA / Drawing）。
# 复用 "office" 这条原始字节透传通道：前端 FileViewer 已在 preset 中合并 office + engineering，
# 后端无需为它们单开 preview_type，只扩展白名单避免被 ZIP/二进制签名误判为 unsupported。
# 需与前端 ENGINEERING_EXTENSIONS 保持一致。
_ENGINEERING_EXTENSIONS = frozenset(
    {
        # XMind
        ".xmind",
        # 压缩包（archive）
        ".zip", ".zipx", ".7z", ".rar", ".tar", ".gz", ".gzip", ".tgz",
        ".bz2", ".bzip2", ".tbz", ".tbz2", ".xz", ".txz", ".lzma", ".zst",
        ".tzst", ".cab", ".ar", ".cpio", ".iso", ".xar", ".lha", ".lzh",
        ".jar", ".war", ".ear", ".apk", ".cbz", ".cbr",
        # CAD
        ".dxf", ".dwg", ".dwf", ".dwfx", ".xps",
        # 3D 模型
        ".glb", ".gltf", ".obj", ".stl", ".ply", ".fbx", ".dae", ".3ds",
        ".3mf", ".amf", ".usd", ".usda", ".usdc", ".usdz", ".kmz",
        ".step", ".stp", ".iges", ".igs", ".ifc", ".3dm", ".brep",
        ".pcd", ".wrl", ".vrml", ".xyz", ".vtk", ".vtp",
        # Geo
        ".geojson", ".kml", ".gpx", ".shp",
        # Typst
        ".typ", ".typst",
        # EDA
        ".olb", ".dra", ".gds", ".oas", ".oasis",
        # Drawing
        ".excalidraw", ".drawio", ".dio", ".mermaid", ".mmd", ".plantuml", ".puml",
        # PSD
        ".psd", ".psb",
    }
)
_OFFICE_MEDIA_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
}
_TEXT_EXTENSIONS = frozenset(
    {
        ".txt",
        ".text",
        ".log",
        ".json",
        ".jsonl",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".csv",
        ".tsv",
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".vue",
        ".css",
        ".less",
        ".scss",
        ".xml",
        ".sql",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".env",
        ".dockerfile",
        ".gitignore",
        ".weather",
    }
)
_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"})
_BINARY_SIGNATURES = (
    b"\x7fELF",
    b"MZ",
    b"%PDF-",
    b"PK\x03\x04",
    b"PK\x05\x06",
    b"PK\x07\x08",
    b"\x89PNG\r\n\x1a\n",
    b"\xff\xd8\xff",
    b"GIF87a",
    b"GIF89a",
    b"RIFF",
)


def is_binary_preview_type(preview_type: str) -> bool:
    """预览时需要原样返回字节流（而非文本内容）的类型。"""
    return preview_type in {"image", "pdf", "office"}


def render_preview_too_large_payload() -> dict:
    return {
        "content": None,
        "preview_type": "unsupported",
        "supported": False,
        "message": "文件过大，当前仅支持 30 MB 以内的文件预览",
        "truncated": False,
        "limit": MAX_BINARY_PREVIEW_SIZE_BYTES,
    }


def detect_preview_type(path: str, raw_content: bytes) -> tuple[str, bool, str | None]:
    suffix = PurePosixPath(path).suffix.lower()
    mime_type, _encoding = mimetypes.guess_type(path)
    head = raw_content[:1024]

    if suffix in _IMAGE_EXTENSIONS or (mime_type and mime_type.startswith("image/")):
        return "image", True, None

    if suffix in _PDF_EXTENSIONS or mime_type == "application/pdf" or head.startswith(b"%PDF-"):
        return "pdf", True, None

    # 办公文档原样交给前端 File Viewer；必须早于下方的 ZIP/二进制签名判定，
    # 否则 OOXML（PK\x03\x04 开头）会被误判为不支持预览。
    if suffix in _OFFICE_EXTENSIONS:
        return "office", True, None

    # preset-engineering 覆盖的格式（XMind / CAD / 3D / 压缩包 / PSD / Geo / Typst / EDA / Drawing）：
    # 同样原样交给前端 File Viewer 渲染。XMind/压缩包本质是 ZIP，必须在此早返回，
    # 否则会被下方的 ZIP 签名分支误判为 unsupported。
    if suffix in _ENGINEERING_EXTENSIONS:
        return "office", True, None

    if suffix in _MARKDOWN_EXTENSIONS:
        return "markdown", True, None

    if suffix in _HTML_EXTENSIONS:
        return "html", True, None

    if suffix in _TEXT_EXTENSIONS:
        return "text", True, None

    if b"\x00" in head:
        return "unsupported", False, "当前文件是二进制文件，暂不支持预览"

    if any(head.startswith(signature) for signature in _BINARY_SIGNATURES):
        if head.startswith(b"RIFF") and b"WEBP" in head[:16]:
            return "image", True, None
        return "unsupported", False, "当前文件格式暂不支持预览"

    if mime_type:
        if mime_type.startswith("text/"):
            return "text", True, None
        if mime_type in {"application/json", "application/xml", "application/javascript"}:
            return "text", True, None
        if mime_type.startswith("application/"):
            return "unsupported", False, "当前文件格式暂不支持预览"

    if not raw_content:
        return "text", True, None

    try:
        raw_content.decode("utf-8")
        return "text", True, None
    except UnicodeDecodeError:
        return "unsupported", False, "当前文件不是可读文本，暂不支持预览"


def render_preview_payload(path: str, raw_content: bytes) -> dict:
    preview_type, supported, message = detect_preview_type(path, raw_content)

    if is_binary_preview_type(preview_type) or not supported:
        return {
            "content": None,
            "preview_type": preview_type,
            "supported": supported,
            "message": message,
            "truncated": False,
            "limit": None,
        }

    try:
        content = raw_content.decode("utf-8")
    except UnicodeDecodeError:
        return {
            "content": None,
            "preview_type": "unsupported",
            "supported": False,
            "message": "当前文件不是 UTF-8 文本，暂不支持预览",
            "truncated": False,
            "limit": None,
        }

    truncated = len(content) > MAX_TEXT_PREVIEW_CHARS
    if truncated:
        content = content[:MAX_TEXT_PREVIEW_CHARS]

    return {
        "content": content,
        "preview_type": preview_type,
        "supported": True,
        "message": message,
        "truncated": truncated,
        "limit": MAX_TEXT_PREVIEW_CHARS,
    }


def detect_media_type(path: str, raw_content: bytes | None = None) -> str:
    """Detect response media type, preferring file signatures over filename suffixes."""
    head = (raw_content or b"")[:512]

    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return "image/gif"
    if head.startswith(b"RIFF") and b"WEBP" in head[:16]:
        return "image/webp"
    if head.startswith(b"BM"):
        return "image/bmp"
    if head.startswith(b"%PDF-"):
        return "application/pdf"

    stripped_head = head.lstrip()
    if stripped_head.startswith(b"<svg") or stripped_head.startswith(b"<?xml"):
        suffix = PurePosixPath(path).suffix.lower()
        if suffix == ".svg" or b"<svg" in stripped_head[:256]:
            return "image/svg+xml"

    suffix = PurePosixPath(path).suffix.lower()
    if suffix in _OFFICE_MEDIA_TYPES:
        return _OFFICE_MEDIA_TYPES[suffix]

    return mimetypes.guess_type(path)[0] or "application/octet-stream"
