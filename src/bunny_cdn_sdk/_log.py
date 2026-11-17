"""SDK logging: structlog events on the stdlib ``bunny_cdn_sdk`` logger, secrets redacted.

The stdlib logger keeps level and handler control with the application
(``logging.getLogger("bunny_cdn_sdk").setLevel(logging.DEBUG)``); structlog only shapes
each event. This never touches global structlog configuration.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import MutableMapping

    import httpx2
    from structlog.typing import Processor

REDACTED = "***"
_MAX_BODY = 2000
_MAX_PARSE = 64 * 1024  # larger bodies (uploads, big lists) are summarised, not logged
# Key names whose values are secrets: AccessKey header, Password/ReadOnlyPassword,
# ZoneSecurityKey, API keys, tokens, cookies.
_SECRET_NAME = re.compile(
    r"key|password|secret|token|authorization|signature|credential|cookie", re.IGNORECASE
)
# A secret-named query parameter's value inside any string (e.g. a logged URL).
_SECRET_QUERY = re.compile(
    r"([?&][^=&#\s]*(?:key|password|secret|token|signature)[^=&#\s]*=)[^&#\s]*", re.IGNORECASE
)

_stdlib_logger = logging.getLogger("bunny_cdn_sdk")


def redact(value: Any, name: str = "") -> Any:
    """Return ``value`` with secret-named fields and query parameters replaced by ``***``."""
    if name and _SECRET_NAME.search(name) and value not in (None, ""):
        return REDACTED
    if isinstance(value, dict):
        return {k: redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return _SECRET_QUERY.sub(rf"\1{REDACTED}", value)
    return value


def _redact_processor(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    return {k: v if k == "event" else redact(v, k) for k, v in event_dict.items()}


_key_value = structlog.processors.KeyValueRenderer(key_order=["event"])


def _render(
    logger: Any, method: str, event_dict: MutableMapping[str, Any]
) -> tuple[tuple[str], dict[str, Any]]:
    """Message as readable ``key=value`` text; the (redacted) fields also ride on the
    record as ``record.bunny_event`` for JSON or structlog formatters."""
    fields = dict(event_dict)
    return (_key_value(logger, method, dict(fields)),), {"extra": {"bunny_event": fields}}


_PROCESSORS: list[Processor] = [
    structlog.stdlib.filter_by_level,
    _redact_processor,
    _render,
]
log: structlog.stdlib.BoundLogger = structlog.wrap_logger(
    _stdlib_logger,
    processors=_PROCESSORS,
    wrapper_class=structlog.stdlib.BoundLogger,
)


def debug_enabled() -> bool:
    """True when DEBUG events would be emitted; guards costly event building."""
    return _stdlib_logger.isEnabledFor(logging.DEBUG)


def _body(content: bytes) -> Any:
    """A body for logging: parsed JSON (so field redaction applies) or truncated text."""
    if not content:
        return None
    if len(content) > _MAX_PARSE:
        return f"<{len(content)} bytes, not logged>"
    try:
        return json.loads(content)
    except ValueError:
        pass
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return f"<{len(content)} bytes of binary data>"
    return text if len(text) <= _MAX_BODY else f"{text[:_MAX_BODY]}... ({len(text)} chars)"


def http_context(
    request: httpx2.Request, response: httpx2.Response | None = None
) -> dict[str, Any]:
    """Event fields for a request and optional response; the logger's processor redacts."""
    ctx: dict[str, Any] = {
        "method": request.method,
        "url": str(request.url),
        "request_headers": dict(request.headers),
    }
    try:
        ctx["request_body"] = _body(request.content)
    except Exception:  # a streamed body can't be read again  # noqa: BLE001
        ctx["request_body"] = "<stream>"
    if response is not None:
        ctx["status"] = response.status_code
        ctx["response_headers"] = dict(response.headers)
        try:
            ctx["response_body"] = _body(response.content)
        except Exception:  # an unread streamed response  # noqa: BLE001
            ctx["response_body"] = "<stream>"
    return ctx
