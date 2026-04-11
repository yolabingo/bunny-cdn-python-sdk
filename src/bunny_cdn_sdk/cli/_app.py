"""Root Typer application, State dataclass, and top-level callback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import typer

app = typer.Typer(no_args_is_help=True, help="Bunny CDN management CLI.")


@dataclass
class State:
    """Auth context and global flags — stored on ctx.obj by @app.callback()."""

    api_key: str = field(default="")
    storage_key: str = field(default="")
    zone_name: str = field(default="")
    region: str = field(default="falkenstein")
    json_output: bool = field(default=False)


@app.callback()
def main(
    ctx: typer.Context,
    api_key: str = typer.Option(
        "",
        envvar="BUNNY_API_KEY",
        help="Bunny CDN account API key. Prefer BUNNY_API_KEY env var.",
    ),
    storage_key: str = typer.Option(
        "",
        envvar="BUNNY_STORAGE_KEY",
        help="Bunny Storage Zone password. Prefer BUNNY_STORAGE_KEY env var.",
    ),
    zone_name: str = typer.Option(
        "",
        envvar="BUNNY_STORAGE_ZONE",
        help="Bunny Storage Zone name. Prefer BUNNY_STORAGE_ZONE env var.",
    ),
    region: str = typer.Option(
        "falkenstein",
        envvar="BUNNY_STORAGE_REGION",
        help="Storage region (default: falkenstein).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output raw JSON instead of formatted table.",
    ),
) -> None:
    """Bunny CDN management CLI — auth options apply to all sub-commands."""
    ctx.ensure_object(State)
    state = cast("State", ctx.obj)
    state.api_key = api_key
    state.storage_key = storage_key
    state.zone_name = zone_name
    state.region = region
    state.json_output = json_output
