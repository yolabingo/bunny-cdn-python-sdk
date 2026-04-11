"""Root Typer application, State dataclass, and top-level callback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import typer

from bunny_cdn_sdk.cli._pull_zone import pull_zone_app
from bunny_cdn_sdk.cli._storage_zone import storage_zone_app
from bunny_cdn_sdk.cli._dns_zone import dns_zone_app
from bunny_cdn_sdk.cli._video_library import video_library_app

app = typer.Typer(no_args_is_help=True, help="Bunny CDN management CLI.")

app.add_typer(pull_zone_app, name="pull-zone")
app.add_typer(storage_zone_app, name="storage-zone")
app.add_typer(dns_zone_app, name="dns-zone")
app.add_typer(video_library_app, name="video-library")


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


@app.command("purge")
def purge_url_cmd(
    ctx: typer.Context,
    url: str = typer.Argument(..., help="URL to purge from CDN cache"),
) -> None:
    """Purge a specific URL from CDN cache."""
    from bunny_cdn_sdk.cli._output import err_console, sdk_errors
    from bunny_cdn_sdk.core import CoreClient
    import typer as _typer
    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise _typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        client.purge_url(url)
        _typer.echo(f"Purged: {url}")
