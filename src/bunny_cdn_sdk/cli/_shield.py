"""Shield (WAF) CLI sub-app."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import typer

from bunny_cdn_sdk import shield
from bunny_cdn_sdk.cli._output import (
    api_client,
    output_result,
    parse_set_pairs,
    sdk_errors,
)

if TYPE_CHECKING:
    from collections.abc import Callable


shield_app = typer.Typer(no_args_is_help=True, help="Manage Bunny Shield (WAF) zones and rules.")
zone_app = typer.Typer(no_args_is_help=True, help="Shield zones.")
waf_app = typer.Typer(no_args_is_help=True, help="WAF rules, profiles and triggered rules.")
custom_rule_app = typer.Typer(no_args_is_help=True, help="Custom WAF rules.")
rate_limit_app = typer.Typer(no_args_is_help=True, help="Rate limit rules.")
access_list_app = typer.Typer(no_args_is_help=True, help="Access lists.")
bot_app = typer.Typer(no_args_is_help=True, help="Bot detection settings.")
event_log_app = typer.Typer(no_args_is_help=True, help="Shield event logs.")
shield_app.add_typer(zone_app, name="zone")
shield_app.add_typer(waf_app, name="waf")
waf_app.add_typer(custom_rule_app, name="custom-rule")
shield_app.add_typer(rate_limit_app, name="rate-limit")
shield_app.add_typer(access_list_app, name="access-list")
shield_app.add_typer(bot_app, name="bot-detection")
shield_app.add_typer(event_log_app, name="event-log")

_ZONE_COLS = ["shieldZoneId", "pullZoneId", "wafEnabled", "wafExecutionMode"]
_RULE_COLS = ["id", "shieldZoneId", "ruleName", "ruleDescription"]
_ACCESS_COLS = ["id", "name", "type", "entryCount"]

SetOpt = typer.Option(..., "--set", help="Field as KEY=VALUE (repeatable; values are JSON-parsed)")
YesOpt = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")


def _run(
    ctx: typer.Context,
    call: Callable[[shield.ShieldClient], Any],
    columns: list[str] | None = None,
    *,
    raw: bool = False,
) -> None:
    """Run ``call(client)`` and print the envelope's ``data`` (all of it if ``raw``)."""
    state, client = api_client(ctx, shield.ShieldClient)
    with sdk_errors():
        result = call(client)
        if not isinstance(result, list) and not raw and isinstance(result, dict):
            result = result.get("data", result)
        if isinstance(result, dict | list) and not result and not state.json_output:
            typer.echo("(none)")
            return
        # Nested/irregular shapes (no columns) go out as JSON.
        output_result(
            result,
            columns=columns,
            json_mode=state.json_output or columns is None,
        )


def _delete(
    ctx: typer.Context, what: str, yes: bool, call: Callable[[shield.ShieldClient], Any]
) -> None:
    _state, client = api_client(ctx, shield.ShieldClient)
    with sdk_errors():
        if not yes:
            typer.confirm(f"Delete {what}?", abort=True)
        call(client)
        typer.echo(f"Deleted {what}.")


# --- zone -------------------------------------------------------------------


@zone_app.command("list")
def zone_list(ctx: typer.Context) -> None:
    """List all Shield zones."""
    _run(ctx, lambda c: list(c.iter_shield_zones()), _ZONE_COLS)


@zone_app.command("get")
def zone_get(ctx: typer.Context, id: int = typer.Argument(..., help="Shield zone ID")) -> None:
    """Get a Shield zone by ID."""
    _run(ctx, lambda c: c.get_shield_zone(id), _ZONE_COLS)


@zone_app.command("get-by-pull-zone")
def zone_get_by_pull_zone(
    ctx: typer.Context, pull_zone_id: int = typer.Argument(..., help="Pull zone ID")
) -> None:
    """Get the Shield zone mapped to a pull zone."""
    _run(ctx, lambda c: c.get_shield_zone_by_pull_zone(pull_zone_id), _ZONE_COLS)


@zone_app.command("create")
def zone_create(
    ctx: typer.Context,
    pull_zone_id: int = typer.Argument(..., help="Pull zone ID"),
    set_: list[str] = typer.Option([], "--set", help="Field as KEY=VALUE (repeatable)"),
) -> None:
    """Create a Shield zone for a pull zone."""
    _run(ctx, lambda c: c.create_shield_zone(pull_zone_id, **parse_set_pairs(set_)))


@zone_app.command("update")
def zone_update(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Shield zone ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Update a Shield zone."""
    _run(ctx, lambda c: c.update_shield_zone(id, **parse_set_pairs(set_)))


# --- waf --------------------------------------------------------------------


@waf_app.command("rules")
def waf_rules(
    ctx: typer.Context, zone_id: int = typer.Argument(..., help="Shield zone ID")
) -> None:
    """List WAF rules."""
    _run(ctx, lambda c: c.list_waf_rules(zone_id))


@waf_app.command("profiles")
def waf_profiles(ctx: typer.Context) -> None:
    """List WAF profiles."""
    _run(ctx, lambda c: c.list_waf_profiles())


@waf_app.command("enums")
def waf_enums(ctx: typer.Context) -> None:
    """Show WAF enum values."""
    _run(ctx, lambda c: c.get_waf_enums())


@waf_app.command("engine-config")
def waf_engine_config(ctx: typer.Context) -> None:
    """Show WAF engine configuration."""
    _run(ctx, lambda c: c.get_waf_engine_config())


@waf_app.command("triggered")
def waf_triggered(
    ctx: typer.Context, zone_id: int = typer.Argument(..., help="Shield zone ID")
) -> None:
    """List triggered WAF rules."""
    _run(ctx, lambda c: c.list_triggered_waf_rules(zone_id))


@waf_app.command("review")
def waf_review(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    rule_id: str = typer.Argument(..., help="Triggered rule ID"),
    action: int = typer.Option(..., "--action", help="0 = Ignore, 1 = LogOnly, 2 = DisableRule"),
) -> None:
    """Review a triggered WAF rule."""
    _run(ctx, lambda c: c.review_triggered_waf_rule(zone_id, rule_id, action))


@custom_rule_app.command("list")
def custom_rule_list(
    ctx: typer.Context, zone_id: int = typer.Argument(..., help="Shield zone ID")
) -> None:
    """List custom WAF rules."""
    _run(ctx, lambda c: list(c.iter_custom_waf_rules(zone_id)), _RULE_COLS)


@custom_rule_app.command("get")
def custom_rule_get(ctx: typer.Context, id: int = typer.Argument(..., help="Rule ID")) -> None:
    """Get a custom WAF rule."""
    _run(ctx, lambda c: c.get_custom_waf_rule(id), _RULE_COLS)


@custom_rule_app.command("create")
def custom_rule_create(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Create a custom WAF rule (e.g. --set ruleName=x --set ruleConfiguration='{...}')."""
    _run(ctx, lambda c: c.create_custom_waf_rule(zone_id, **parse_set_pairs(set_)))


@custom_rule_app.command("update")
def custom_rule_update(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Rule ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Update a custom WAF rule."""
    _run(ctx, lambda c: c.update_custom_waf_rule(id, **parse_set_pairs(set_)))


@custom_rule_app.command("delete")
def custom_rule_delete(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Rule ID"),
    yes: bool = YesOpt,
) -> None:
    """Delete a custom WAF rule (prompts for confirmation)."""
    _delete(ctx, f"custom WAF rule {id}", yes, lambda c: c.delete_custom_waf_rule(id))


# --- rate-limit -------------------------------------------------------------


@rate_limit_app.command("list")
def rate_limit_list(
    ctx: typer.Context, zone_id: int = typer.Argument(..., help="Shield zone ID")
) -> None:
    """List rate limits."""
    _run(ctx, lambda c: list(c.iter_rate_limits(zone_id)), _RULE_COLS)


@rate_limit_app.command("get")
def rate_limit_get(ctx: typer.Context, id: int = typer.Argument(..., help="Rate limit ID")) -> None:
    """Get a rate limit."""
    _run(ctx, lambda c: c.get_rate_limit(id), _RULE_COLS)


@rate_limit_app.command("create")
def rate_limit_create(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Create a rate limit."""
    _run(ctx, lambda c: c.create_rate_limit(zone_id, **parse_set_pairs(set_)))


@rate_limit_app.command("update")
def rate_limit_update(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Rate limit ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Update a rate limit."""
    _run(ctx, lambda c: c.update_rate_limit(id, **parse_set_pairs(set_)))


@rate_limit_app.command("delete")
def rate_limit_delete(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Rate limit ID"),
    yes: bool = YesOpt,
) -> None:
    """Delete a rate limit (prompts for confirmation)."""
    _delete(ctx, f"rate limit {id}", yes, lambda c: c.delete_rate_limit(id))


# --- access-list ------------------------------------------------------------


@access_list_app.command("list")
def access_list_list(
    ctx: typer.Context, zone_id: int = typer.Argument(..., help="Shield zone ID")
) -> None:
    """List access lists (managed and custom)."""
    _run(ctx, lambda c: c.list_access_lists(zone_id))


@access_list_app.command("get")
def access_list_get(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    id: int = typer.Argument(..., help="Access list ID"),
) -> None:
    """Get an access list."""
    _run(ctx, lambda c: c.get_access_list(zone_id, id), _ACCESS_COLS)


@access_list_app.command("create")
def access_list_create(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Create a custom access list."""
    _run(ctx, lambda c: c.create_access_list(zone_id, **parse_set_pairs(set_)))


@access_list_app.command("update")
def access_list_update(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    id: int = typer.Argument(..., help="Access list ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Update a custom access list."""
    _run(ctx, lambda c: c.update_access_list(zone_id, id, **parse_set_pairs(set_)))


@access_list_app.command("configure")
def access_list_configure(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    id: int = typer.Argument(..., help="Access list configuration ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Update an access list's configuration (isEnabled, action)."""
    _run(ctx, lambda c: c.update_access_list_configuration(zone_id, id, **parse_set_pairs(set_)))


@access_list_app.command("delete")
def access_list_delete(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    id: int = typer.Argument(..., help="Access list ID"),
    yes: bool = YesOpt,
) -> None:
    """Delete a custom access list (prompts for confirmation)."""
    _delete(ctx, f"access list {id}", yes, lambda c: c.delete_access_list(zone_id, id))


# --- bot-detection ----------------------------------------------------------


@bot_app.command("get")
def bot_get(ctx: typer.Context, zone_id: int = typer.Argument(..., help="Shield zone ID")) -> None:
    """Get bot detection configuration."""
    _run(ctx, lambda c: c.get_bot_detection(zone_id))


@bot_app.command("update")
def bot_update(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Update bot detection configuration."""
    _run(ctx, lambda c: c.update_bot_detection(zone_id, **parse_set_pairs(set_)))


# --- event-log / metrics ----------------------------------------------------


@event_log_app.command("get")
def event_log_get(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    date: str = typer.Argument(..., help="Date as MM-dd-yyyy"),
    continuation_token: str = typer.Argument(
        ..., help="Continuation token ('_' style value from the API)"
    ),
) -> None:
    """Get event logs for a date."""
    _run(ctx, lambda c: c.get_event_logs(zone_id, date, continuation_token), raw=True)


@event_log_app.command("search")
def event_log_search(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Search event logs."""
    _run(ctx, lambda c: c.search_event_logs(zone_id, **parse_set_pairs(set_)), raw=True)


@shield_app.command("metrics")
def metrics(ctx: typer.Context, zone_id: int = typer.Argument(..., help="Shield zone ID")) -> None:
    """Show the metrics overview for a Shield zone."""
    _run(ctx, lambda c: c.get_metrics_overview(zone_id))
