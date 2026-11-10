"""Root Typer application, State dataclass, and top-level callback."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, cast

import typer
from typer.core import TyperGroup

from bunny_cdn_sdk import __version__, core
from bunny_cdn_sdk.cli._dns_zone import dns_zone_app
from bunny_cdn_sdk.cli._load_balancer import load_balancer_app
from bunny_cdn_sdk.cli._logs import logs_cmd
from bunny_cdn_sdk.cli._output import (
    OutputFormat,
    api_client,
    output_result,
    sdk_errors,
    set_output_format,
)
from bunny_cdn_sdk.cli._partner import partner_app
from bunny_cdn_sdk.cli._pull_zone import pull_zone_app
from bunny_cdn_sdk.cli._schema import add_footer, build_schema
from bunny_cdn_sdk.cli._shield import shield_app
from bunny_cdn_sdk.cli._storage import storage_app
from bunny_cdn_sdk.cli._storage_zone import storage_zone_app
from bunny_cdn_sdk.cli._video_library import video_library_app

# Help panels group the top-level commands in `bunnycdn --help`, in this order.
_CDN, _STORAGE, _NETWORK = "CDN", "Storage", "DNS & Load Balancing"
_STREAM, _SECURITY, _ACCOUNT = "Stream", "Security", "Account"
_PARTNER, _TOOLS = "Partner (uses --partner-api-key)", "CLI LLM Tools"
_PANELS = [_CDN, _STORAGE, _NETWORK, _STREAM, _SECURITY, _ACCOUNT, _PARTNER, _TOOLS]


class _PanelOrderGroup(TyperGroup):
    """List commands panel by panel (Typer otherwise puts all commands before sub-groups)."""

    def list_commands(self, ctx: Any) -> list[str]:  # Click context (vendored by Typer)
        def panel(name: str) -> int:
            p = getattr(self.commands[name], "rich_help_panel", None)
            return _PANELS.index(p) if p in _PANELS else len(_PANELS)

        return sorted(super().list_commands(ctx), key=panel)


app = typer.Typer(cls=_PanelOrderGroup, no_args_is_help=True, help="Bunny CDN management CLI.")

app.add_typer(pull_zone_app, name="pull-zone", rich_help_panel=_CDN)
app.command("logs", rich_help_panel=_CDN)(logs_cmd)
app.add_typer(storage_zone_app, name="storage-zone", rich_help_panel=_STORAGE)
app.add_typer(storage_app, name="storage", rich_help_panel=_STORAGE)
app.add_typer(dns_zone_app, name="dns-zone", rich_help_panel=_NETWORK)
app.add_typer(load_balancer_app, name="load-balancer", rich_help_panel=_NETWORK)
app.add_typer(video_library_app, name="video-library", rich_help_panel=_STREAM)
app.add_typer(shield_app, name="shield", rich_help_panel=_SECURITY)
app.add_typer(partner_app, name="partner", rich_help_panel=_PARTNER)


@dataclass
class State:
    """Auth context and global flags — stored on ctx.obj by @app.callback()."""

    api_key: str = field(default="")
    partner_api_key: str = field(default="")
    storage_key: str = field(default="")
    zone_name: str = field(default="")
    region: str = field(default="falkenstein")
    output_format: OutputFormat = field(default=OutputFormat.human)

    @property
    def json_output(self) -> bool:
        """True for ``json`` and ``json-file``: commands emit JSON instead of tables."""
        return self.output_format != OutputFormat.human


@app.callback()
def main(
    ctx: typer.Context,
    api_key: str = typer.Option(
        "",
        envvar="BUNNY_API_KEY",
        help=(
            "Bunny account API key, used by every command except `partner`. "
            "Prefer BUNNY_API_KEY env var."
        ),
    ),
    partner_api_key: str = typer.Option(
        "",
        envvar="BUNNY_PARTNER_API_KEY",
        help=(
            "Partner API key (from your partner account), used only by `partner` commands; "
            "falls back to --api-key. Prefer BUNNY_PARTNER_API_KEY env var."
        ),
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
    output_format: OutputFormat = typer.Option(
        OutputFormat.human,
        "--output-format",
        envvar="BUNNY_OUTPUT_FORMAT",
        case_sensitive=False,
        help=(
            "human: tables and text. json: JSON on stdout. json-file: JSON written to a new "
            "temp file whose path is printed. With json/json-file, errors are JSON on stderr."
        ),
    ),
) -> None:
    """Bunny CDN management CLI — auth options apply to all sub-commands."""
    ctx.ensure_object(State)
    state = cast("State", ctx.obj)
    state.api_key = api_key
    state.partner_api_key = partner_api_key
    state.storage_key = storage_key
    state.zone_name = zone_name
    state.region = region
    state.output_format = output_format
    set_output_format(output_format)


_GB = 1024**3
_K = 1000


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


@app.command("purge", rich_help_panel=_CDN)
def purge_url_cmd(
    ctx: typer.Context,
    url: str = typer.Argument(..., help="URL to purge from CDN cache"),
) -> None:
    """Purge a specific URL from CDN cache."""
    _state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        client.purge_url(url)
        typer.echo(f"Purged: {url}")


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


@app.command("stats", rich_help_panel=_CDN)
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
    state, client = api_client(ctx, core.CoreClient)

    today = datetime.now(tz=UTC).date()
    date_from = from_ or (today - timedelta(days=7)).isoformat()
    date_to = to_ or today.isoformat()

    with sdk_errors():
        if pull_zone_id is not None:
            zone = client.get_pull_zone(pull_zone_id)
            stats = client.get_statistics(pullZone=pull_zone_id, dateFrom=date_from, dateTo=date_to)
            rows = [_build_stats_row(zone["Name"], stats)]
        else:
            zones = list(client.iter_pull_zones())

            def _fetch_one(z: dict) -> dict:
                s = client.get_statistics(pullZone=z["Id"], dateFrom=date_from, dateTo=date_to)
                return _build_stats_row(z.get("Name", ""), s)

            with ThreadPoolExecutor(max_workers=max(1, min(len(zones), 20))) as pool:
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
            typer.echo(f"  {date_from} → {date_to}  ({days} days)")


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


@app.command("billing", rich_help_panel=_ACCOUNT)
def billing_cmd(ctx: typer.Context) -> None:
    """Display account billing summary."""
    state, client = api_client(ctx, core.CoreClient)

    with sdk_errors():
        billing = client.get_billing()
        output_result(billing, columns=_BILLING_COLUMNS, json_mode=state.json_output)


@app.command("schema", rich_help_panel=_TOOLS)
def schema_cmd() -> None:
    """Print every command, argument, option and env var as JSON (for scripts and AI agents)."""
    output_result(build_schema(app, "bunnycdn", __version__), json_mode=True)


add_footer(app)  # last, so it reaches every command registered above
