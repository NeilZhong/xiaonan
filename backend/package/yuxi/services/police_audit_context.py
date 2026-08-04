"""★ 审计元数据上下文 — 在请求生命周期内传递 ip / user_agent，供审计写入自动捕获。

使用 contextvars 而非函数参数透传，避免污染各业务调用点（service 层大多没有 Request）。
由 server.main 的 AuditMetaMiddleware 在每个请求开始时写入，请求结束后自动随上下文销毁。
"""

from contextvars import ContextVar

# 当前请求的客户端 IP（来自 x-forwarded-for 或 socket）
REQUEST_IP: ContextVar[str | None] = ContextVar("audit_request_ip", default=None)
# 当前请求的 User-Agent
REQUEST_UA: ContextVar[str | None] = ContextVar("audit_request_ua", default=None)


def set_request_meta(ip: str | None, ua: str | None) -> None:
    """由中间件在请求入口写入（覆盖式，新请求重置为本次值）。"""
    REQUEST_IP.set(ip)
    REQUEST_UA.set(ua)


def get_request_ip() -> str | None:
    return REQUEST_IP.get()


def get_request_ua() -> str | None:
    return REQUEST_UA.get()
