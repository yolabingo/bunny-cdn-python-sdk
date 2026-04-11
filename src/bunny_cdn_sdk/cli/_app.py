"""Root Typer application, State dataclass, and top-level callback."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import cast

import typer

from bunny_cdn_sdk.cli._dns_zone import dns_zone_app
from bunny_cdn_sdk.cli._pull_zone import pull_zone_app
from bunny_cdn_sdk.cli._storage import storage_app
from bunny_cdn_sdk.cli._storage_zone import storage_zone_app
from bunny_cdn_sdk.cli._video_library import video_library_app

app = typer.Typer(no_args_is_help=True, help="Bunny CDN management CLI.")

app.add_typer(pull_zone_app, name="pull-zone")
app.add_typer(storage_zone_app, name="storage-zone")
app.add_typer(dns_zone_app, name="dns-zone")
app.add_typer(video_library_app, name="video-library")
app.add_typer(storage_app, name="storage")


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


def _fmt_bytes(n: int) -> str:
    """Format byte count as human-readable string."""
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n / 1024:.1f} KB"
    if n < 1024**3:
        return f"{n / 1024**2:.1f} MB"
    return f"{n / 1024**3:.1f} GB"


def _build_stats_row(name: str, stats: dict | None) -> dict:
    """Build a display row dict from a zone name and statistics API response."""
    if stats is None:
        stats = {}
    served = stats.get("RequestsServed", 0) or 0
    err3xx = stats.get("Error3xxTotal", 0) or 0
    err4xx = stats.get("Error4xxTotal", 0) or 0
    err5xx = stats.get("Error5xxTotal", 0) or 0
    total_err = err3xx + err4xx + err5xx
    error_pct = f"{total_err / served * 100:.2f}%" if served else "—"
    return {
        "Name": name,
        "RequestsServed": served,
        "BandwidthUsed": _fmt_bytes(stats.get("BandwidthUsed", 0) or 0),
        "BandwidthCached": _fmt_bytes(stats.get("BandwidthCachedUsed", 0) or 0),
        "CacheHitRate": stats.get("CacheHitRate", 0),
        "Error%": error_pct,
    }


@app.command("purge")
def purge_url_cmd(
    ctx: typer.Context,
    url: str = typer.Argument(..., help="URL to purge from CDN cache"),
) -> None:
    """Purge a specific URL from CDN cache."""
    import typer as _typer

    from bunny_cdn_sdk.cli._output import err_console, sdk_errors
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise _typer.Exit(1)
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        client.purge_url(url)
        _typer.echo(f"Purged: {url}")


_STATS_COLUMNS = [
    "Name",
    "RequestsServed",
    "BandwidthUsed",
    "BandwidthCached",
    "CacheHitRate",
    "Error%",
]


@app.command("stats")
def stats_cmd(
    ctx: typer.Context,
    pull_zone_id: int | None = typer.Option(
        None, "--pull-zone-id", help="Narrow report to a single pull zone ID"
    ),
    from_: str | None = typer.Option(None, "--from", help="Start date (ISO, default: 7 days ago)"),
    to_: str | None = typer.Option(None, "--to", help="End date (ISO, default: today)"),
) -> None:
    """Display CDN statistics per pull zone."""
    import typer as _typer

    from bunny_cdn_sdk.cli._output import err_console, output_result, sdk_errors
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise _typer.Exit(1)

    date_from = from_ or (date.today() - timedelta(days=7)).isoformat()
    date_to = to_ or date.today().isoformat()

    with sdk_errors():
        client = CoreClient(api_key=state.api_key)

        if pull_zone_id is not None:
            zone = client.get_pull_zone(pull_zone_id)
            stats = client.get_statistics(
                pullZoneId=pull_zone_id, dateFrom=date_from, dateTo=date_to
            )
            rows = [_build_stats_row(zone["Name"], stats)]
        else:
            zones = list(client.iter_pull_zones())

            def _fetch_one(z: dict) -> dict:
                s = client.get_statistics(pullZoneId=z["Id"], dateFrom=date_from, dateTo=date_to)
                return _build_stats_row(z.get("Name", ""), s)

            with ThreadPoolExecutor(max_workers=min(len(zones), 20)) as pool:
                rows = list(pool.map(_fetch_one, zones))

        output_result(rows, columns=_STATS_COLUMNS, json_mode=state.json_output)


_BILLING_COLUMNS = [
    "Balance",
    "ThisMonthCharges",
    "UnpaidInvoicesAmount",
    "MonthlyChargesStorage",
    "MonthlyChargesEUTraffic",
    "MonthlyChargesUSTraffic",
    "MonthlyChargesASIATraffic",
    "MonthlyChargesAFRICATraffic",
]


@app.command("billing")
def billing_cmd(ctx: typer.Context) -> None:
    """Display account billing summary."""
    import typer as _typer

    from bunny_cdn_sdk.cli._output import err_console, output_result, sdk_errors
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise _typer.Exit(1)

    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        billing = client.get_billing()
        output_result(billing, columns=_BILLING_COLUMNS, json_mode=state.json_output)
