"""Video library CLI sub-app."""

from __future__ import annotations

from typing import cast

import typer
from rich.table import Table
from rich.text import Text

from bunny_cdn_sdk.cli._output import console, err_console, output_result, sdk_errors

video_library_app = typer.Typer(no_args_is_help=True, help="Manage Bunny CDN video libraries.")
_COLUMNS = ["Name", "VideoCount", "Id"]


@video_library_app.command("list")
def list_libs(ctx: typer.Context) -> None:
    """List all video libraries."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        libs = sorted(client.iter_video_libraries(), key=lambda v: v.get("Name", ""))
        output_result(libs, columns=_COLUMNS, json_mode=state.json_output)


@video_library_app.command("get")
def get_lib(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Video library ID"),
) -> None:
    """Get a video library by ID."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        lib = client.get_video_library(id)
        output_result(lib, columns=_COLUMNS, json_mode=state.json_output)


@video_library_app.command("create")
def create_lib(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", help="Video library name"),
) -> None:
    """Create a new video library."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        result = client.create_video_library(Name=name)
        output_result(result, columns=_COLUMNS, json_mode=state.json_output)


@video_library_app.command("delete")
def delete_lib(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Video library ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a video library (prompts for confirmation)."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        lib = client.get_video_library(id)
        name = lib.get("Name", "")
        if not yes:
            typer.confirm(f"Delete video library {id} ({name})?", abort=True)
        client.delete_video_library(id)
        typer.echo(f"Deleted video library {id} ({name}).")


@video_library_app.command("update")
def update_lib(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Video library ID"),
    set_: list[str] = typer.Option([], "--set", help="Field to update as KEY=VALUE (repeatable)"),
) -> None:
    """Update video library fields using --set KEY=VALUE."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        # Parse KEY=VALUE pairs (ValueError caught by sdk_errors)
        updates: dict[str, str] = {}
        for pair in set_:
            if "=" not in pair:
                raise ValueError(f"Invalid --set value: '{pair}' (expected KEY=VALUE)")
            k, v = pair.split("=", 1)
            updates[k] = v
        client = CoreClient(api_key=state.api_key)
        # D-12: fetch before state
        before = client.get_video_library(id)
        # Apply update
        after = client.update_video_library(id, **updates)
        # D-15: json mode outputs updated resource
        if state.json_output:
            output_result(after, json_mode=True)
            return
        # D-13, D-14: diff table with only changed rows in red italic
        changed_keys = [k for k in updates if str(before.get(k, "")) != str(after.get(k, ""))]
        if not changed_keys:
            typer.echo("No fields changed.")
            return
        table = Table("Field", "Before", "After")
        for k in changed_keys:
            table.add_row(
                k,
                Text(str(before.get(k, "")), style="bold red italic"),
                Text(str(after.get(k, "")), style="bold red italic"),
            )
        console.print(table)
