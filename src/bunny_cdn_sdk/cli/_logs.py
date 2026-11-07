"""CDN request logs CLI command."""

from __future__ import annotations

from itertools import islice

import typer

from bunny_cdn_sdk import logs
from bunny_cdn_sdk.cli._output import api_client, output_result, sdk_errors

_COLUMNS = ["timestamp", "statusCode", "cacheStatus", "countryCode", "remoteIp", "url"]


def logs_cmd(
    ctx: typer.Context,
    pull_zone_id: int = typer.Argument(..., help="Pull zone ID"),
    from_: str | None = typer.Option(None, "--from", help="Start time (ISO 8601)"),
    to: str | None = typer.Option(None, "--to", help="End time (ISO 8601)"),
    status: str | None = typer.Option(None, "--status", help="Status filter, e.g. 200,5xx"),
    cache_status: str | None = typer.Option(None, "--cache-status", help="Cache status, e.g. HIT"),
    country: str | None = typer.Option(None, "--country", help="Country code, e.g. US"),
    search: str | None = typer.Option(None, "--search", help="Search text"),
    limit: int = typer.Option(100, "--limit", min=1, help="Max rows to show"),
    order: str | None = typer.Option(None, "--order", help="Sort order: asc or desc"),
) -> None:
    """Show CDN request logs for a pull zone."""
    state, client = api_client(ctx, logs.LoggingClient)
    params = {
        "from": from_,
        "to": to,
        "status": status,
        "cacheStatus": cache_status,
        "country": country,
        "search": search,
        "order": order,
    }
    params = {k: v for k, v in params.items() if v is not None}
    with sdk_errors():
        rows = list(islice(client.iter_logs(pull_zone_id, limit=min(limit, 1000), **params), limit))
        output_result(rows, columns=_COLUMNS, json_mode=state.json_output)
