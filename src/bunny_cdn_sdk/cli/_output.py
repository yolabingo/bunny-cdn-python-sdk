"""Output helpers: sdk_errors() context manager, output_result(), _cell()."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

import typer
from rich.console import Console
from rich.table import Table

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


@contextmanager
def sdk_errors() -> Generator[None, None, None]:
    """Wrap a command body — maps SDK exceptions to stderr message + Exit(1)."""
    try:
        yield
    except BunnyAuthenticationError:
        err_console.print("Authentication failed. Check your API key.")
        raise typer.Exit(1) from None
    except BunnyNotFoundError as exc:
        err_console.print(f"Not found: {exc.message}")
        raise typer.Exit(1) from None
    except BunnyRateLimitError:
        err_console.print("Rate limited. Try again later.")
        raise typer.Exit(1) from None
    except BunnyServerError as exc:
        err_console.print(f"Server error: {exc.message}")
        raise typer.Exit(1) from None
    except BunnyAPIError as exc:
        err_console.print(f"API error {exc.status_code}: {exc.message}")
        raise typer.Exit(1) from None
    except BunnyTimeoutError as exc:
        err_console.print(f"Timeout: {exc}")
        raise typer.Exit(1) from None
    except BunnyConnectionError as exc:
        err_console.print(f"Connection error: {exc}")
        raise typer.Exit(1) from None
    except BunnySDKError as exc:
        err_console.print(f"SDK error: {exc}")
        raise typer.Exit(1) from None
    except ValueError as exc:
        err_console.print(f"Invalid argument: {exc}")
        raise typer.Exit(1) from None


def output_result(
    data: Any,
    *,
    columns: list[str] | None = None,
    json_mode: bool = False,
    _console: Console | None = None,
) -> None:
    """Emit command output — JSON if json_mode, Rich table otherwise."""
    _con = _console or console

    if json_mode:
        typer.echo(json.dumps(data, indent=2, default=str))
        return

    # Passthrough for plain strings and other non-dict/list scalars
    if not isinstance(data, (dict, list)):
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

    table = Table(*col_names)
    for row in rows:
        table.add_row(*[_cell(row.get(col)) for col in col_names])

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
