"""Root Typer application, State dataclass, and top-level callback."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, cast

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


_KB = 1024
_MB = 1024**2
_GB = 1024**3
_K = 1000


def _fmt_bytes(n: int) -> str:
    """Format byte count as GB (rounded to int, comma-separated)."""
    return f"{round(n / _GB):,} GB"


def _build_stats_row(name: str, stats: dict | None) -> dict:
    """Build a display row dict from a zone name and statistics API response."""
    if stats is None:
        stats = {}
    served = stats.get("TotalRequestsServed", 0) or 0
    err3xx = sum((stats.get("Error3xxChart") or {}).values())
    err4xx = sum((stats.get("Error4xxChart") or {}).values())
    err5xx = sum((stats.get("Error5xxChart") or {}).values())
    total_err = err3xx + err4xx + err5xx
    error_pct = f"{total_err / served * 100:.2f}%" if served else "—"
    bw_used = stats.get("TotalBandwidthUsed", 0) or 0
    bw_cached = sum((stats.get("BandwidthCachedChart") or {}).values())
    return {
        "Name": name,
        "Requests\n(K)": f"{round(served / _K):,}" if served >= _K else str(served),
        "Bandwidth\nUsed (GB)": f"{round(bw_used / _GB):,}",
        "Bandwidth\nCached (GB)": f"{round(bw_cached / _GB):,}",
        "Cache\nHit\nRate (%)": str(round(stats.get("CacheHitRate", 0))),
        "Error\n(%)": error_pct.rstrip("%") if error_pct != "—" else "—",
        "_requests": served,
        "_bw_used": bw_used,
        "_bw_cached": bw_cached,
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
    "Requests\n(K)",
    "Bandwidth\nUsed (GB)",
    "Bandwidth\nCached (GB)",
    "Cache\nHit\nRate (%)",
    "Error\n(%)",
]


class _StatSort(StrEnum):
    Name = "Name"
    RequestsServed = "RequestsServed"
    BandwidthUsed = "BandwidthUsed"
    BandwidthCached = "BandwidthCached"
    CacheHitRate = "CacheHitRate"
    Error = "Error"


def _stats_sort_key(row: dict, field: _StatSort) -> Any:
    if field == _StatSort.Name:
        return row["Name"].lower()
    if field == _StatSort.RequestsServed:
        return -(row.get("_requests", 0) or 0)
    if field == _StatSort.BandwidthUsed:
        return -(row.get("_bw_used", 0) or 0)
    if field == _StatSort.BandwidthCached:
        return -(row.get("_bw_cached", 0) or 0)
    if field == _StatSort.CacheHitRate:
        val = row.get("Cache\nHit\nRate (%)", "0")
        return -(float(str(val)) if val else 0.0)
    # Error — parse "1.60" or "—"
    val = row.get("Error\n(%)", "—")
    return -(float(val) if val != "—" else 0.0)


@app.command("stats")
def stats_cmd(
    ctx: typer.Context,
    pull_zone_id: int | None = typer.Option(
        None, "--pull-zone-id", help="Narrow report to a single pull zone ID"
    ),
    from_: str | None = typer.Option(None, "--from", help="Start date (ISO, default: 7 days ago)"),
    to_: str | None = typer.Option(None, "--to", help="End date (ISO, default: today)"),
    sort_by: _StatSort = typer.Option(
        _StatSort.Name,
        "--sort-by",
        help="Column to sort by (Name sorts A→Z; others sort highest first)",
    ),
) -> None:
    """Display CDN statistics per pull zone."""
    import typer as _typer

    from bunny_cdn_sdk.cli._output import err_console, output_result, sdk_errors
    from bunny_cdn_sdk.core import CoreClient

    state = cast("State", ctx.obj)
    if not state.api_key:
        err_console.print("Missing API key. Use --api-key or set BUNNY_API_KEY.")
        raise _typer.Exit(1)

    today = datetime.now(tz=UTC).date()
    date_from = from_ or (today - timedelta(days=7)).isoformat()
    date_to = to_ or today.isoformat()

    with sdk_errors():
        client = CoreClient(api_key=state.api_key)

        if pull_zone_id is not None:
            zone = client.get_pull_zone(pull_zone_id)
            stats = client.get_statistics(pullZone=pull_zone_id, dateFrom=date_from, dateTo=date_to)
            rows = [_build_stats_row(zone["Name"], stats)]
        else:
            zones = list(client.iter_pull_zones())

            def _fetch_one(z: dict) -> dict:
                s = client.get_statistics(pullZone=z["Id"], dateFrom=date_from, dateTo=date_to)
                return _build_stats_row(z.get("Name", ""), s)

            with ThreadPoolExecutor(max_workers=min(len(zones), 20)) as pool:
                rows = list(pool.map(_fetch_one, zones))

        rows.sort(key=lambda r: _stats_sort_key(r, sort_by))

        # Map enum value to actual column name with newlines
        _highlight_map = {
            _StatSort.Name: "Name",
            _StatSort.RequestsServed: "Requests\n(K)",
            _StatSort.BandwidthUsed: "Bandwidth\nUsed (GB)",
            _StatSort.BandwidthCached: "Bandwidth\nCached (GB)",
            _StatSort.CacheHitRate: "Cache\nHit\nRate (%)",
            _StatSort.Error: "Error\n(%)",
        }
        highlight = _highlight_map[sort_by]

        # Compute totals from raw numeric values
        total_req = sum(r.get("_requests", 0) or 0 for r in rows)
        total_bw_used = sum(r.get("_bw_used", 0) or 0 for r in rows)
        total_bw_cached = sum(r.get("_bw_cached", 0) or 0 for r in rows)
        footer: dict = {
            "Name": "TOTAL",
            "Requests\n(K)": f"{round(total_req / _K):,}" if total_req >= _K else str(total_req),
            "Bandwidth\nUsed (GB)": f"{round(total_bw_used / _GB):,}",
            "Bandwidth\nCached (GB)": f"{round(total_bw_cached / _GB):,}",
            "Cache\nHit\nRate (%)": "",
            "Error\n(%)": "",
        }

        # Strip internal sort keys before rendering
        clean_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]

        from datetime import date as _date

        days = (_date.fromisoformat(date_to) - _date.fromisoformat(date_from)).days + 1

        output_result(
            clean_rows,
            columns=_STATS_COLUMNS,
            json_mode=state.json_output,
            highlight_col=None if state.json_output else highlight,
            footer_row=None if state.json_output else footer,
        )

        if not state.json_output:
            _typer.echo(f"  {date_from} → {date_to}  ({days} days)")


_BILLING_COLUMNS = [
    "Balance",
    "ThisMonthCharges",
    "MonthlyChargesStorage",
    "MonthlyChargesDNS",
    "MonthlyChargesEUTraffic",
    "MonthlyChargesUSTraffic",
    "MonthlyChargesASIATraffic",
    "MonthlyChargesAFTraffic",
    "MonthlyChargesSATraffic",
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
