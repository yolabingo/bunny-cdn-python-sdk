"""Bunny CDN CLI — optional extra. Install with: pip install 'bunny-cdn-sdk[cli]'."""

from __future__ import annotations

_MSG = (
    "The bunnycdn CLI requires optional dependencies.\n"
    "Install them with:  pip install 'bunny-cdn-sdk[cli]'"
)

try:
    import typer  # noqa: F401
    from rich.console import Console  # noqa: F401

    from bunny_cdn_sdk.cli._app import app
except ImportError as _err:
    raise ImportError(_MSG) from _err

__all__ = ["app"]
