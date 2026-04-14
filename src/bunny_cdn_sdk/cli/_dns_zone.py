"""DNS zone CLI sub-app (includes record sub-commands)."""

from __future__ import annotations

from typing import cast

import typer
from rich.table import Table
from rich.text import Text

from bunny_cdn_sdk.cli._output import console, err_console, output_result, sdk_errors

dns_zone_app = typer.Typer(no_args_is_help=True, help="Manage Bunny CDN DNS zones.")
record_app = typer.Typer(no_args_is_help=True, help="Manage DNS records within a zone.")
dns_zone_app.add_typer(record_app, name="record")

_ZONE_COLUMNS = ["Domain", "RecordsCount", "Id"]
_RECORD_COLUMNS = ["Name", "Type", "Value", "Id"]


@dns_zone_app.command("list")
def list_zones(ctx: typer.Context) -> None:
    """List all DNS zones."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        zones = sorted(client.iter_dns_zones(), key=lambda z: z.get("Domain", ""))
        output_result(zones, columns=_ZONE_COLUMNS, json_mode=state.json_output)


@dns_zone_app.command("get")
def get_zone(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="DNS zone ID"),
) -> None:
    """Get a DNS zone by ID."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        zone = client.get_dns_zone(id)
        output_result(zone, columns=_ZONE_COLUMNS, json_mode=state.json_output)


@dns_zone_app.command("create")
def create_zone(
    ctx: typer.Context,
    domain: str = typer.Option(..., "--domain", help="Domain name for the DNS zone"),
) -> None:
    """Create a new DNS zone."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        result = client.create_dns_zone(Domain=domain)
        output_result(result, columns=_ZONE_COLUMNS, json_mode=state.json_output)


@dns_zone_app.command("delete")
def delete_zone(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="DNS zone ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a DNS zone (prompts for confirmation)."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        zone = client.get_dns_zone(id)
        domain = zone.get("Domain", "")
        if not yes:
            typer.confirm(f"Delete DNS zone {id} ({domain})?", abort=True)
        client.delete_dns_zone(id)
        typer.echo(f"Deleted DNS zone {id} ({domain}).")


@record_app.command("add")
def add_record(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="DNS zone ID"),
    type_: str = typer.Option(..., "--type", help="Record type (A, AAAA, CNAME, MX, TXT, etc.)"),
    name: str = typer.Option(..., "--name", help="Record name"),
    value: str = typer.Option(..., "--value", help="Record value"),
    ttl: int = typer.Option(300, "--ttl", help="TTL in seconds (default: 300)"),
) -> None:
    """Add a DNS record to a zone."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        result = client.add_dns_record(zone_id, Type=type_, Name=name, Value=value, Ttl=ttl)
        output_result(result, columns=_RECORD_COLUMNS, json_mode=state.json_output)


@record_app.command("update")
def update_record(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="DNS zone ID"),
    record_id: int = typer.Argument(..., help="DNS record ID"),
    set_: list[str] = typer.Option([], "--set", help="Field to update as KEY=VALUE (repeatable)"),
) -> None:
    """Update a DNS record using --set KEY=VALUE."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        updates: dict[str, str] = {}
        for pair in set_:
            if "=" not in pair:
                msg = f"Invalid --set value: '{pair}' (expected KEY=VALUE)"
                raise ValueError(msg)
            k, v = pair.split("=", 1)
            updates[k] = v
        client = CoreClient(api_key=state.api_key)
        # D-12: fetch zone to get the record's before state
        zone_before = client.get_dns_zone(zone_id)
        records_before = zone_before.get("Records", [])
        before_record = next((r for r in records_before if r.get("Id") == record_id), {})
        # Apply update
        after = client.update_dns_record(zone_id, record_id, **updates)
        # D-15: json mode outputs updated resource
        if state.json_output:
            output_result(after, json_mode=True)
            return
        # D-13, D-14: diff table with only changed rows in red italic
        changed_keys = [
            k for k in updates if str(before_record.get(k, "")) != str(after.get(k, ""))
        ]
        if not changed_keys:
            typer.echo("No fields changed.")
            return
        table = Table("Field", "Before", "After")
        for k in changed_keys:
            table.add_row(
                k,
                Text(str(before_record.get(k, "")), style="bold red italic"),
                Text(str(after.get(k, "")), style="bold red italic"),
            )
        console.print(table)


@record_app.command("delete")
def delete_record(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="DNS zone ID"),
    record_id: int = typer.Argument(..., help="DNS record ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a DNS record (prompts for confirmation)."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        if not yes:
            typer.confirm(f"Delete DNS record {record_id} in zone {zone_id}?", abort=True)
        client.delete_dns_record(zone_id, record_id)
        typer.echo(f"Deleted DNS record {record_id} in zone {zone_id}.")
