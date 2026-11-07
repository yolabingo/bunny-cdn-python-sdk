"""Load balancer CLI sub-app."""

from __future__ import annotations

from typing import Any

import typer

from bunny_cdn_sdk import core
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
_SET_HELP = "Field as KEY=VALUE (repeatable)"


def _range(from_: str | None, to: str | None) -> dict[str, Any]:
    return {k: v for k, v in (("from", from_), ("to", to)) if v is not None}


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


@load_balancer_app.command("create")
def create_load_balancer(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", help="Load balancer name"),
    set_: list[str] = typer.Option([], "--set", help=_SET_HELP),
) -> None:
    """Create a load balancer."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        fields = parse_set_pairs(set_)
        result = client.create_load_balancer(Name=name, **fields)
        output_result(result, columns=_LB_COLUMNS, json_mode=state.json_output)


@load_balancer_app.command("update")
def update_load_balancer(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Load balancer ID"),
    set_: list[str] = typer.Option([], "--set", help=_SET_HELP),
) -> None:
    """Update load balancer fields using --set KEY=VALUE."""
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


@load_balancer_app.command("stats")
def load_balancer_stats(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Load balancer ID"),
    from_: str | None = typer.Option(None, "--from", help="Start date"),
    to: str | None = typer.Option(None, "--to", help="End date"),
    hourly: bool = typer.Option(False, "--hourly", help="Hourly granularity"),
) -> None:
    """Get load balancer statistics."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        query = _range(from_, to)
        if hourly:
            query["hourly"] = True
        output_result(client.get_load_balancer_statistics(id, **query), json_mode=state.json_output)


@load_balancer_app.command("pull-zones")
def load_balancer_pull_zones(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Load balancer ID"),
    from_: str | None = typer.Option(None, "--from", help="Start date"),
    to: str | None = typer.Option(None, "--to", help="End date"),
) -> None:
    """Get pull zones attached to a load balancer."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        result = client.get_load_balancer_pull_zones(id, **_range(from_, to))
        output_result(result, json_mode=state.json_output)


@load_balancer_app.command("account-stats")
def load_balancer_account_stats(
    ctx: typer.Context,
    from_: str | None = typer.Option(None, "--from", help="Start date"),
    to: str | None = typer.Option(None, "--to", help="End date"),
) -> None:
    """Get account-wide load balancer statistics."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        result = client.get_load_balancer_account_statistics(**_range(from_, to))
        output_result(result, json_mode=state.json_output)


@load_balancer_app.command("usage")
def load_balancer_usage(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Load balancer ID"),
    year: int | None = typer.Option(None, "--year", help="Year"),
    month: int | None = typer.Option(None, "--month", help="Month"),
) -> None:
    """Get load balancer usage."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        query = {k: v for k, v in (("year", year), ("month", month)) if v is not None}
        output_result(client.get_load_balancer_usage(id, **query), json_mode=state.json_output)


# --- origin groups ---------------------------------------------------------


@origin_group_app.command("add")
def add_origin_group(
    ctx: typer.Context,
    lb_id: int = typer.Argument(..., help="Load balancer ID"),
    set_: list[str] = typer.Option([], "--set", help=_SET_HELP),
) -> None:
    """Add an origin group."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        output_result(
            client.add_origin_group(lb_id, **parse_set_pairs(set_)), json_mode=state.json_output
        )


@origin_group_app.command("update")
def update_origin_group(
    ctx: typer.Context,
    lb_id: int = typer.Argument(..., help="Load balancer ID"),
    group_id: int = typer.Argument(..., help="Origin group ID"),
    set_: list[str] = typer.Option([], "--set", help=_SET_HELP),
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


@origin_app.command("add")
def add_origin(
    ctx: typer.Context,
    lb_id: int = typer.Argument(..., help="Load balancer ID"),
    group_id: int = typer.Argument(..., help="Origin group ID"),
    set_: list[str] = typer.Option([], "--set", help=_SET_HELP),
) -> None:
    """Add an origin to a group."""
    with sdk_errors():
        state, client = api_client(ctx, core.CoreClient)
        result = client.add_origin(lb_id, group_id, **parse_set_pairs(set_))
        output_result(result, json_mode=state.json_output)


@origin_app.command("update")
def update_origin(
    ctx: typer.Context,
    lb_id: int = typer.Argument(..., help="Load balancer ID"),
    group_id: int = typer.Argument(..., help="Origin group ID"),
    origin_id: int = typer.Argument(..., help="Origin ID"),
    set_: list[str] = typer.Option([], "--set", help=_SET_HELP),
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
