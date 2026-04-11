"""Output helpers: sdk_errors() context manager, output_result(), _cell()."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

import typer
from rich.console import Console

from bunny_cdn_sdk._exceptions import (
    BunnyAPIError,
    BunnyAuthenticationError,
    BunnyConnectionError,
    BunnyNotFoundError,
    BunnyRateLimitError,
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
    except ValueError as exc:
        err_console.print(f"Invalid argument: {exc}")
        raise typer.Exit(1) from None


def output_result(data: Any, *, json_mode: bool = False) -> None:  # noqa: ANN401
    """Emit command output — JSON if json_mode, Rich table rendering in Phase 09."""
    if json_mode:
        typer.echo(json.dumps(data, indent=2, default=str))
        return
    # Phase 09 will replace this with Rich table rendering
    typer.echo(str(data))


def _cell(value: object) -> str:
    """Format a dict/list/scalar value as a single table cell string."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    if isinstance(value, list):
        return f"[{len(value)} items]"
    return str(value)
