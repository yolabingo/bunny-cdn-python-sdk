"""Pull zone CLI sub-app."""

from __future__ import annotations

import typer
from rich.table import Table
from rich.text import Text

from bunny_cdn_sdk import core
from bunny_cdn_sdk.cli._options import SET_HELP, examples
from bunny_cdn_sdk.cli._output import (
    api_client,
    console,
    output_result,
    parse_set_pairs,
    sdk_errors,
)

pull_zone_app = typer.Typer(no_args_is_help=True, help="Manage Bunny CDN pull zones.")
_COLUMNS = ["Name", "OriginUrl", "Enabled", "Id"]


@pull_zone_app.command("list")
def list_zones(ctx: typer.Context) -> None:
    """List all pull zones."""
    state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        zones = sorted(client.iter_pull_zones(), key=lambda z: z.get("Name") or "")
        output_result(zones, columns=_COLUMNS, json_mode=state.json_output)


@pull_zone_app.command("get")
def get_zone(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Pull zone ID"),
) -> None:
    """Get a pull zone by ID."""
    state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        zone = client.get_pull_zone(id)
        output_result(zone, columns=_COLUMNS, json_mode=state.json_output)


@pull_zone_app.command(
    "create",
    epilog=examples(
        "bunnycdn pull-zone create --name my-site \\",
        "  --origin-url https://origin.example.com",
    ),
)
def create_zone(
    ctx: typer.Context,
    name: str = typer.Option(
        ...,
        "--name",
        help="Pull zone name: lowercase letters, numbers and hyphens; becomes NAME.b-cdn.net",
    ),
    origin_url: str = typer.Option(
        ...,
        "--origin-url",
        help="Origin server URL the zone pulls from, e.g. https://origin.example.com",
    ),
) -> None:
    """Create a new pull zone."""
    state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        result = client.create_pull_zone(Name=name, OriginUrl=origin_url)
        output_result(result, columns=_COLUMNS, json_mode=state.json_output)


@pull_zone_app.command("delete")
def delete_zone(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Pull zone ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a pull zone (prompts for confirmation)."""
    _state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        zone = client.get_pull_zone(id)
        name = zone.get("Name", "")
        if not yes:
            typer.confirm(f"Delete pull zone {id} ({name})?", abort=True)
        client.delete_pull_zone(id)
        typer.echo(f"Deleted pull zone {id} ({name}).")


@pull_zone_app.command(
    "purge",
    epilog=examples(
        "bunnycdn pull-zone purge 12345",
        "bunnycdn pull-zone purge 12345 --tag product-images",
        "bunnycdn pull-zone purge 12345 --tag a --tag b",
    ),
)
def purge_zone(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Pull zone ID"),
    tag: list[str] = typer.Option(
        [], "--tag", help="Purge only files with this cache tag; repeat for several tags"
    ),
) -> None:
    """Purge cache for a pull zone: everything, or only files with a cache tag.

    A full purge counts toward Bunny's stricter prefix purge rate limit
    (about 30 per minute); a tag purge counts toward the exact limit
    (about 300 per minute). Tag purging is not supported on zones with
    Perma-Cache.
    """
    _state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        if not tag:
            client.purge_pull_zone_cache(id)
            typer.echo(f"Purged cache for pull zone {id}.")
        for t in tag:
            client.purge_pull_zone_cache(id, CacheTag=t)
            typer.echo(f"Purged cache tag {t!r} for pull zone {id}.")


@pull_zone_app.command(
    "update",
    epilog=examples(
        "bunnycdn pull-zone update 12345 --set EnableLogging=true",
        "bunnycdn pull-zone update 12345 --set OriginUrl=https://o.example.com",
        "bunnycdn pull-zone update 12345 --set CacheControlMaxAgeOverride=86400",
    ),
)
def update_zone(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Pull zone ID"),
    set_: list[str] = typer.Option([], "--set", help=SET_HELP),
) -> None:
    """Update pull zone fields using --set KEY=VALUE.

    Only the fields you pass change; the output lists what differed.
    """
    state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        updates = parse_set_pairs(set_)  # ValueError is caught by sdk_errors
        # D-12: fetch before state
        before = client.get_pull_zone(id)
        # Apply update
        after = client.update_pull_zone(id, **updates)
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


# --- edge rules ------------------------------------------------------------

edge_rule_app = typer.Typer(no_args_is_help=True, help="Manage pull zone edge rules.")
pull_zone_app.add_typer(edge_rule_app, name="edge-rule")
_EDGE_COLUMNS = ["Guid", "Description", "ActionType", "Enabled"]


@edge_rule_app.command("list")
def list_edge_rules(
    ctx: typer.Context,
    pull_zone_id: int = typer.Argument(..., help="Pull zone ID"),
) -> None:
    """List edge rules of a pull zone."""
    state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        rules = client.get_pull_zone(pull_zone_id).get("EdgeRules") or []
        output_result(rules, columns=_EDGE_COLUMNS, json_mode=state.json_output)


@edge_rule_app.command(
    "set",
    epilog=examples(
        "# add a rule: no Guid",
        "bunnycdn pull-zone edge-rule set 12345 --set Enabled=true \\",
        "  --set Description=Block-bots --set OrderIndex=0",
        "# update a rule: pass its Guid (from edge-rule list)",
        "bunnycdn pull-zone edge-rule set 12345 --set Guid=<guid> \\",
        "  --set Enabled=false",
    ),
)
def set_edge_rule(
    ctx: typer.Context,
    pull_zone_id: int = typer.Argument(..., help="Pull zone ID"),
    set_: list[str] = typer.Option([], "--set", help=SET_HELP),
) -> None:
    """Add an edge rule, or update one when --set Guid=... is given.

    Without Guid a new rule is added; with the Guid of an existing rule
    (shown by `edge-rule list`) that rule is updated.
    """
    state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        fields = parse_set_pairs(set_)
        result = client.add_or_update_edge_rule(pull_zone_id, **fields)
        output_result(result, json_mode=state.json_output)


@edge_rule_app.command("delete")
def delete_edge_rule(
    ctx: typer.Context,
    pull_zone_id: int = typer.Argument(..., help="Pull zone ID"),
    guid: str = typer.Argument(..., help="Edge rule GUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete an edge rule (prompts for confirmation)."""
    _state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        if not yes:
            typer.confirm(f"Delete edge rule {guid} from pull zone {pull_zone_id}?", abort=True)
        client.delete_edge_rule(pull_zone_id, guid)
        typer.echo(f"Deleted edge rule {guid}.")


def _toggle(ctx: typer.Context, pull_zone_id: int, guid: str, *, enabled: bool) -> None:
    _state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        client.set_edge_rule_enabled(pull_zone_id, guid, enabled=enabled)
        typer.echo(f"{'Enabled' if enabled else 'Disabled'} edge rule {guid}.")


@edge_rule_app.command("enable")
def enable_edge_rule(
    ctx: typer.Context,
    pull_zone_id: int = typer.Argument(..., help="Pull zone ID"),
    guid: str = typer.Argument(..., help="Edge rule GUID"),
) -> None:
    """Enable an edge rule."""
    _toggle(ctx, pull_zone_id, guid, enabled=True)


@edge_rule_app.command("disable")
def disable_edge_rule(
    ctx: typer.Context,
    pull_zone_id: int = typer.Argument(..., help="Pull zone ID"),
    guid: str = typer.Argument(..., help="Edge rule GUID"),
) -> None:
    """Disable an edge rule."""
    _toggle(ctx, pull_zone_id, guid, enabled=False)
