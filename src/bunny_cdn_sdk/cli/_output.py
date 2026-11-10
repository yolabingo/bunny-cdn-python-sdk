"""Output helpers: sdk_errors() context manager, output_result(), _cell()."""

from __future__ import annotations

import json
import tempfile
from contextlib import contextmanager
from enum import StrEnum
from typing import TYPE_CHECKING, Any, NoReturn, Protocol, cast

if TYPE_CHECKING:
    from collections.abc import Generator

    from bunny_cdn_sdk.cli._app import State

import typer
from rich.console import Console
from rich.table import Column, Table

from bunny_cdn_sdk._exceptions import (
    BunnyAPIError,
    BunnyAuthenticationError,
    BunnyConnectionError,
    BunnyNotFoundError,
    BunnyRateLimitError,
    BunnySDKError,
    BunnyServerError,
    BunnyTimeoutError,
)

console = Console()
err_console = Console(stderr=True)


class OutputFormat(StrEnum):
    """``--output-format`` choices."""

    human = "human"
    json = "json"
    json_file = "json-file"


# Set by the root callback on every run (one CLI run per process).
_format = OutputFormat.human


def set_output_format(fmt: OutputFormat) -> None:
    """Choose this run's output format (called from the root callback)."""
    global _format  # noqa: PLW0603
    _format = fmt


def _file_prefix() -> str:
    """``bunnycdn-partner-customer-list``: the running command's names, no argument values."""
    try:
        # Typer vendors Click privately; the root callback runs before the sub-command is
        # known, so the leaf context is the only place the full command path exists.
        from typer._click.globals import get_current_context
    except ImportError:  # pragma: no cover - a future Typer moved it; use a generic name
        return "bunnycdn"
    ctx = get_current_context(silent=True)
    words = ctx.command_path.split()[1:] if ctx else []
    return "-".join(["bunnycdn", *words])


def _write_json_file(data: Any) -> None:
    """Write ``data`` to a new uniquely named temp file and print its path."""
    with tempfile.NamedTemporaryFile(
        "w", prefix=f"{_file_prefix()}-", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(data, f, indent=2, default=str)
    typer.echo(f.name)


def fail(
    code: str, message: str, *, status: int | None = None, retryable: bool = False
) -> NoReturn:
    """Report an error on stderr and exit 1.

    Plain text in ``human`` format. With ``json`` or ``json-file``: one line of
    ``{"error": {"code", "message", "status", "retryable"}}`` so scripts and agents
    can branch on ``code`` and retry only when ``retryable`` is true.
    """
    if _format != OutputFormat.human:
        payload = {"code": code, "message": message, "status": status, "retryable": retryable}
        typer.echo(json.dumps({"error": payload}), err=True)
    else:
        err_console.print(message)
    raise typer.Exit(1)


def require_api_key(state: Any, *, partner: bool = False) -> str:
    """Return the API key to use; exit 1 with a message if none was supplied.

    With ``partner``, the partner key wins and the account key is the fallback.
    """
    key = (state.partner_api_key or state.api_key) if partner else state.api_key
    if not key:
        fail(
            "missing_api_key",
            "Missing partner API key. Use --partner-api-key or set BUNNY_PARTNER_API_KEY "
            "(or --api-key / BUNNY_API_KEY)."
            if partner
            else "Missing API key. Use --api-key or set BUNNY_API_KEY.",
        )
    return key


class _KeyedClient(Protocol):
    def __init__(self, api_key: str) -> None: ...


def api_client[C: _KeyedClient](
    ctx: typer.Context, cls: type[C], *, partner: bool = False
) -> tuple[State, C]:
    """Return ``(state, cls(api_key=...))`` for a command; exit 1 if no API key."""
    state = cast("State", ctx.obj)
    return state, cls(api_key=require_api_key(state, partner=partner))


def require_storage_auth(state: Any) -> None:
    """Exit 1 with a message if storage zone name or key is missing."""
    if not state.zone_name or not state.storage_key:
        fail(
            "missing_storage_auth",
            "Missing storage auth. Use --zone-name/--storage-key "
            "or set BUNNY_STORAGE_ZONE/BUNNY_STORAGE_KEY.",
        )


def _classify(exc: Exception) -> tuple[str, str, bool]:  # noqa: PLR0911
    """Return ``(code, message, retryable)`` for an error raised inside a command."""
    status = getattr(exc, "status_code", None)
    message = getattr(exc, "message", None) or str(exc)
    if isinstance(exc, BunnyAuthenticationError):
        return "authentication_failed", "Authentication failed. Check your API key.", False
    if isinstance(exc, BunnyNotFoundError):
        return "not_found", f"Not found: {message}", False
    if isinstance(exc, BunnyRateLimitError):
        return "rate_limited", "Rate limited. Try again later.", True
    if isinstance(exc, BunnyServerError):
        return "server_error", f"Server error: {message}", True
    if isinstance(exc, BunnyAPIError):
        return "api_error", f"API error {status}: {message}", False
    if isinstance(exc, BunnyTimeoutError):
        return "timeout", f"Timeout: {exc}", True
    if isinstance(exc, BunnyConnectionError):
        return "connection_error", f"Connection error: {exc}", True
    if isinstance(exc, BunnySDKError):
        return "sdk_error", f"SDK error: {exc}", False
    return "invalid_argument", f"Invalid argument: {exc}", False


@contextmanager
def sdk_errors() -> Generator[None, None, None]:
    """Wrap a command body — maps SDK errors (and ValueError) to ``fail()``."""
    try:
        yield
    except (BunnySDKError, ValueError) as exc:
        code, message, retryable = _classify(exc)
        fail(code, message, status=getattr(exc, "status_code", None), retryable=retryable)


def output_result(
    data: Any,
    *,
    columns: list[str] | None = None,
    json_mode: bool = False,
    highlight_col: str | None = None,
    footer_row: dict[str, Any] | None = None,
    _console: Console | None = None,
) -> None:
    """Emit command output — JSON if json_mode, Rich table otherwise."""
    _con = _console or console

    if json_mode:
        if _format == OutputFormat.json_file:
            _write_json_file(data)
        else:
            typer.echo(json.dumps(data, indent=2, default=str))
        return

    # Passthrough for plain strings and other non-dict/list scalars
    if not isinstance(data, dict | list):
        typer.echo(str(data))
        return

    # Normalize single dict to list so all rendering uses the same code path
    rows: list[dict[str, Any]] = [data] if isinstance(data, dict) else data  # type: ignore[assignment]

    # Guard: list of scalars — render each element as a plain line
    if rows and not isinstance(rows[0], dict):
        for item in rows:
            typer.echo(str(item))
        return

    if not rows:
        # Empty list — print empty table with headers if columns provided, else nothing
        if columns:
            table = Table(*columns)
            _con.print(table)
        return

    # Derive column order: explicit list takes priority; fallback to first row's keys
    col_names: list[str] = columns if columns is not None else list(rows[0].keys())

    col_specs: list[Column | str] = [
        Column(header=f"{name} \u2193", header_style="yellow bold", no_wrap=True)
        if name == highlight_col
        else name
        for name in col_names
    ]
    table = Table(*col_specs)
    for row in rows:
        table.add_row(*[_cell(row.get(col)) for col in col_names])

    if footer_row is not None:
        table.add_section()
        table.add_row(*[_cell(footer_row.get(col)) for col in col_names])

    _con.print(table)


def _cell(value: object) -> str:
    """Format a dict/list/scalar value as a single table cell string."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    if isinstance(value, list):
        return f"[{len(value)} items]"
    return str(value)


def parse_set_pairs(pairs: list[str]) -> dict[str, Any]:
    """Parse repeated ``--set KEY=VALUE`` options into an update dict.

    Values are read as JSON when possible (``false`` -> False, ``600`` -> 600), so
    booleans and numbers reach the API with the right type; anything else stays a
    string. Quote a value to force a string: ``--set Name='"123"'``.
    """
    updates: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            msg = f"Invalid --set value: '{pair}' (expected KEY=VALUE)"
            raise ValueError(msg)
        key, value = pair.split("=", 1)
        try:
            updates[key] = json.loads(value)
        except ValueError:
            updates[key] = value
    return updates
