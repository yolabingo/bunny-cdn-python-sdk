"""Load balancer CLI sub-app."""

from __future__ import annotations

from typing import Any

import typer

from bunny_cdn_sdk import core
from bunny_cdn_sdk.cli._options import SET_HELP, date_range, examples, from_option, to_option
from bunny_cdn_sdk.cli._output import (
    api_client,
    output_result,
    parse_set_pairs,
    sdk_errors,
)

load_balancer_app = typer.Typer(no_args_is_help=True, help="Manage Bunny CDN load balancers.")
origin_group_app = typer.Typer(no_args_is_help=True, help="Manage load balancer origin groups.")
origin_app = typer.Typer(no_args_is_help=True, help="Manage origins within an origin group.")
load_balancer_app.add_typer(origin_group_app, name="origin-group")
load_balancer_app.add_typer(origin_app, name="origin")

_COLUMNS = ["Id", "Name", "Enabled"]  # origin groups and origins
_LB_COLUMNS = ["LoadBalancerId", "Name", "OriginGroupLoadBalancingMethod"]


def _range(from_: str, to: str) -> dict[str, Any]:
    start, end = date_range(from_, to)
    return {"from": start.date().isoformat(), "to": end.date().isoformat()}  # API rounds to days


@load_balancer_app.command("list")
def list_load_balancers(
    ctx: typer.Context,
    page: int = typer.Option(1, "--page", help="Page number"),
    count: int = typer.Option(50, "--count", help="Items per page"),
) -> None:
    """List load balancers."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        output_result(
            client.list_load_balancers(page=page, count=count),
            columns=_LB_COLUMNS,
            json_mode=state.json_output,
        )


@load_balancer_app.command("get")
def get_load_balancer(
    ctx: typer.Context, id: int = typer.Argument(..., help="Load balancer ID")
) -> None:
    """Get a load balancer by ID."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        output_result(
            client.get_load_balancer(id), columns=_LB_COLUMNS, json_mode=state.json_output
        )


@load_balancer_app.command(
    "create",
    epilog=examples(
        "bunnycdn load-balancer create --name my-lb",
        "bunnycdn load-balancer create --name my-lb --set StickySessionType=1",
    ),
)
def create_load_balancer(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", help="Load balancer name, e.g. my-lb"),
    set_: list[str] = typer.Option([], "--set", help=SET_HELP),
) -> None:
    """Create a load balancer."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        fields = parse_set_pairs(set_)
        result = client.create_load_balancer(Name=name, **fields)
        output_result(result, columns=_LB_COLUMNS, json_mode=state.json_output)


@load_balancer_app.command(
    "update",
    epilog=examples(
        "bunnycdn load-balancer update 12345 --set Name=my-lb-2",
    ),
)
def update_load_balancer(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Load balancer ID"),
    set_: list[str] = typer.Option([], "--set", help=SET_HELP),
) -> None:
    """Update load balancer fields using --set KEY=VALUE.

    Only the fields you pass change.
    """
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        result = client.update_load_balancer(id, **parse_set_pairs(set_))
        output_result(result, columns=_LB_COLUMNS, json_mode=state.json_output)


@load_balancer_app.command("delete")
def delete_load_balancer(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Load balancer ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a load balancer (prompts for confirmation)."""
    with sdk_errors():
        _, client = api_client(ctx, core.CoreClient)
        name = client.get_load_balancer(id).get("Name", "")
        if not yes:
            typer.confirm(f"Delete load balancer {id} ({name})?", abort=True)
        client.delete_load_balancer(id)
        typer.echo(f"Deleted load balancer {id} ({name}).")


@load_balancer_app.command(
    "stats",
    epilog=examples(
        "bunnycdn load-balancer stats 12345                       # last 7d",
        "bunnycdn load-balancer stats 12345 --from 30d --hourly",
        "bunnycdn load-balancer stats 12345 --from 2026-10-01 --to 2026-10-31",
    ),
)
def load_balancer_stats(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Load balancer ID"),
    from_: str = from_option("7d"),
    to: str = to_option("today"),
    hourly: bool = typer.Option(False, "--hourly", help="Hourly instead of daily data points"),
) -> None:
    """Get load balancer statistics."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        query = _range(from_, to)
        if hourly:
            query["hourly"] = True
        output_result(client.get_load_balancer_statistics(id, **query), json_mode=state.json_output)


@load_balancer_app.command(
    "pull-zones",
    epilog=examples(
        "bunnycdn load-balancer pull-zones 12345",
        "bunnycdn load-balancer pull-zones 12345 --from 30d",
        "bunnycdn load-balancer pull-zones 12345 --from 2026-10-01 --to 2026-10-31",
    ),
)
def load_balancer_pull_zones(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Load balancer ID"),
    from_: str = from_option("7d"),
    to: str = to_option("today"),
) -> None:
    """Get pull zones attached to a load balancer."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        result = client.get_load_balancer_pull_zones(id, **_range(from_, to))
        output_result(result, json_mode=state.json_output)


@load_balancer_app.command(
    "account-stats",
    epilog=examples(
        "bunnycdn load-balancer account-stats",
        "bunnycdn load-balancer account-stats --from 30d",
        "bunnycdn load-balancer account-stats --from 2026-10-01 --to 2026-10-31",
    ),
)
def load_balancer_account_stats(
    ctx: typer.Context,
    from_: str = from_option("7d"),
    to: str = to_option("today"),
) -> None:
    """Get account-wide load balancer statistics."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        result = client.get_load_balancer_account_statistics(**_range(from_, to))
        output_result(result, json_mode=state.json_output)


@load_balancer_app.command(
    "usage",
    epilog=examples(
        "bunnycdn load-balancer usage 12345",
        "bunnycdn load-balancer usage 12345 --year 2026 --month 10",
    ),
)
def load_balancer_usage(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Load balancer ID"),
    year: int | None = typer.Option(
        None, "--year", help="Year, e.g. 2026 (default: this year, UTC)"
    ),
    month: int | None = typer.Option(
        None, "--month", min=1, max=12, help="Month 1-12 (default: this month, UTC)"
    ),
) -> None:
    """Get load balancer usage."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        query = {k: v for k, v in (("year", year), ("month", month)) if v is not None}
        output_result(client.get_load_balancer_usage(id, **query), json_mode=state.json_output)


# --- origin groups ---------------------------------------------------------


@origin_group_app.command(
    "add",
    epilog=examples(
        "bunnycdn load-balancer origin-group add 12345 --set Name=eu \\",
        "  --set Enabled=true --set Priority=0",
    ),
)
def add_origin_group(
    ctx: typer.Context,
    lb_id: int = typer.Argument(..., help="Load balancer ID"),
    set_: list[str] = typer.Option([], "--set", help=SET_HELP),
) -> None:
    """Add an origin group."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        output_result(
            client.add_origin_group(lb_id, **parse_set_pairs(set_)), json_mode=state.json_output
        )


@origin_group_app.command(
    "update",
    epilog=examples(
        "bunnycdn load-balancer origin-group update 12345 8 --set Weight=50",
    ),
)
def update_origin_group(
    ctx: typer.Context,
    lb_id: int = typer.Argument(..., help="Load balancer ID"),
    group_id: int = typer.Argument(..., help="Origin group ID"),
    set_: list[str] = typer.Option([], "--set", help=SET_HELP),
) -> None:
    """Update an origin group using --set KEY=VALUE."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        result = client.update_origin_group(lb_id, group_id, **parse_set_pairs(set_))
        output_result(result, json_mode=state.json_output)


@origin_group_app.command("delete")
def delete_origin_group(
    ctx: typer.Context,
    lb_id: int = typer.Argument(..., help="Load balancer ID"),
    group_id: int = typer.Argument(..., help="Origin group ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete an origin group (prompts for confirmation)."""
    with sdk_errors():
        _, client = api_client(ctx, core.CoreClient)
        if not yes:
            typer.confirm(f"Delete origin group {group_id} from load balancer {lb_id}?", abort=True)
        client.delete_origin_group(lb_id, group_id)
        typer.echo(f"Deleted origin group {group_id}.")


# --- origins ---------------------------------------------------------------


@origin_app.command(
    "add",
    epilog=examples(
        "bunnycdn load-balancer origin add 12345 8 --set Name=origin-1 \\",
        "  --set Enabled=true --set Weight=100",
    ),
)
def add_origin(
    ctx: typer.Context,
    lb_id: int = typer.Argument(..., help="Load balancer ID"),
    group_id: int = typer.Argument(..., help="Origin group ID"),
    set_: list[str] = typer.Option([], "--set", help=SET_HELP),
) -> None:
    """Add an origin to a group."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        result = client.add_origin(lb_id, group_id, **parse_set_pairs(set_))
        output_result(result, json_mode=state.json_output)


@origin_app.command(
    "update",
    epilog=examples(
        "bunnycdn load-balancer origin update 12345 8 21 --set Enabled=false",
    ),
)
def update_origin(
    ctx: typer.Context,
    lb_id: int = typer.Argument(..., help="Load balancer ID"),
    group_id: int = typer.Argument(..., help="Origin group ID"),
    origin_id: int = typer.Argument(..., help="Origin ID"),
    set_: list[str] = typer.Option([], "--set", help=SET_HELP),
) -> None:
    """Update an origin using --set KEY=VALUE."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        result = client.update_origin(lb_id, group_id, origin_id, **parse_set_pairs(set_))
        output_result(result, json_mode=state.json_output)


@origin_app.command("delete")
def delete_origin(
    ctx: typer.Context,
    lb_id: int = typer.Argument(..., help="Load balancer ID"),
    group_id: int = typer.Argument(..., help="Origin group ID"),
    origin_id: int = typer.Argument(..., help="Origin ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete an origin (prompts for confirmation)."""
    with sdk_errors():
        _, client = api_client(ctx, core.CoreClient)
        if not yes:
            typer.confirm(f"Delete origin {origin_id} from group {group_id}?", abort=True)
        client.delete_origin(lb_id, group_id, origin_id)
        typer.echo(f"Deleted origin {origin_id}.")
