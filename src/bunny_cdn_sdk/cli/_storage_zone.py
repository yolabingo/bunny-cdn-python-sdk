"""Storage zone CLI sub-app."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import typer
from rich.table import Table
from rich.text import Text

from bunny_cdn_sdk.cli._output import console, err_console, output_result, sdk_errors

if TYPE_CHECKING:
    pass

storage_zone_app = typer.Typer(no_args_is_help=True, help="Manage Bunny CDN storage zones.")
_COLUMNS = ["Name", "Region", "Id"]


@storage_zone_app.command("list")
def list_zones(ctx: typer.Context) -> None:
    """List all storage zones."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        zones = sorted(client.iter_storage_zones(), key=lambda z: z.get("Name", ""))
        output_result(zones, columns=_COLUMNS, json_mode=state.json_output)


@storage_zone_app.command("get")
def get_zone(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Storage zone ID"),
) -> None:
    """Get a storage zone by ID."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        zone = client.get_storage_zone(id)
        output_result(zone, columns=_COLUMNS, json_mode=state.json_output)


@storage_zone_app.command("create")
def create_zone(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", help="Storage zone name"),
) -> None:
    """Create a new storage zone."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        result = client.create_storage_zone(Name=name)
        output_result(result, columns=_COLUMNS, json_mode=state.json_output)


@storage_zone_app.command("delete")
def delete_zone(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Storage zone ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a storage zone (prompts for confirmation)."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        zone = client.get_storage_zone(id)
        name = zone.get("Name", "")
        if not yes:
            typer.confirm(f"Delete storage zone {id} ({name})?", abort=True)
        client.delete_storage_zone(id)
        typer.echo(f"Deleted storage zone {id} ({name}).")


@storage_zone_app.command("update")
def update_zone(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Storage zone ID"),
    set_: list[str] = typer.Option(
        [], "--set", help="Field to update as KEY=VALUE (repeatable)"
    ),
) -> None:
    """Update storage zone fields using --set KEY=VALUE."""
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
        before = client.get_storage_zone(id)
        # Apply update
        after = client.update_storage_zone(id, **updates)
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
