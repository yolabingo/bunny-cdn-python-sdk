"""CDN request logs CLI command."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from itertools import islice

import typer

from bunny_cdn_sdk import logs
from bunny_cdn_sdk.cli import _options
from bunny_cdn_sdk.cli._options import date_range, examples, from_option, to_option
from bunny_cdn_sdk.cli._output import api_client, output_result, sdk_errors

_COLUMNS = ["timestamp", "statusCode", "cacheStatus", "countryCode", "remoteIp", "url"]
_RETENTION = timedelta(days=3)  # the API keeps 3 days and serves at most a 3-day range

EPILOG = examples(
    "bunnycdn logs 12345                         # last 24h, newest first",
    "bunnycdn logs 12345 --from 2h --status 5xx  # recent server errors",
    "bunnycdn logs 12345 --status 404,403 --cache-status MISS --country US",
    "bunnycdn logs 12345 --from 2026-11-16T08:00Z --to 2026-11-16T09:00Z",
    "bunnycdn logs 12345 --from 1h --order asc --limit 1000",
)


class _Order(StrEnum):
    asc = "asc"
    desc = "desc"


def _utc(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def logs_cmd(
    ctx: typer.Context,
    pull_zone_id: int = typer.Argument(..., help="Pull zone ID"),
    from_: str = from_option("24h"),
    to: str = to_option("now"),
    status: str | None = typer.Option(
        None, "--status", help="Comma-separated codes or classes (OR-ed), e.g. 200,404,5xx"
    ),
    cache_status: str | None = typer.Option(
        None, "--cache-status", help="Cache status, e.g. HIT or MISS"
    ),
    country: str | None = typer.Option(None, "--country", help="Two-letter country code, e.g. US"),
    search: str | None = typer.Option(None, "--search", help="Free-text search"),
    limit: int = typer.Option(100, "--limit", min=1, help="Max rows to show"),
    order: _Order = typer.Option(_Order.desc, "--order", help="By timestamp"),
) -> None:
    """Show CDN request logs for a pull zone (kept for 3 days; at most 3 days per query)."""
    start, end = date_range(from_, to)
    if end - start > _RETENTION:
        msg = "the range can be at most 3 days"
        raise typer.BadParameter(msg, param_hint="--from/--to")
    if start < _options.utcnow() - _RETENTION:
        msg = f"logs are kept for 3 days; {from_!r} is older"
        raise typer.BadParameter(msg, param_hint="--from")
    state, client = api_client(ctx, logs.LoggingClient)
    params = {
        "from": _utc(start),
        "to": _utc(end),
        "status": status,
        "cacheStatus": cache_status,
        "country": country,
        "search": search,
        "order": order.value,
    }
    params = {k: v for k, v in params.items() if v is not None}
    with sdk_errors():
        rows = list(islice(client.iter_logs(pull_zone_id, limit=min(limit, 1000), **params), limit))
        output_result(rows, columns=_COLUMNS, json_mode=state.json_output)
