"""Shield (WAF) CLI sub-app."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import typer

from bunny_cdn_sdk import shield
from bunny_cdn_sdk.cli._options import SET_HELP, WHEN_FORMATS, examples, when
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

SetOpt = typer.Option(..., "--set", help=SET_HELP)
YesOpt = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")


_REVIEW_ACTIONS = {"ignore": 0, "log-only": 1, "disable-rule": 2}


def _review_action(value: str) -> int:
    """Map an --action name (any case) or number 0-2 to the API's integer."""
    key = value.strip().lower()
    if key in _REVIEW_ACTIONS:
        return _REVIEW_ACTIONS[key]
    if key in {"0", "1", "2"}:
        return int(key)
    choices = ", ".join(f"{n} ({i})" for n, i in _REVIEW_ACTIONS.items())
    msg = f"{value!r} is not valid; choose one of: {choices}"
    raise typer.BadParameter(msg, param_hint="--action")


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


@zone_app.command(
    "create",
    epilog=examples(
        "bunnycdn shield zone create 12345",
        "bunnycdn shield zone create 12345 --set wafEnabled=true \\",
        "  --set learningMode=true",
    ),
)
def zone_create(
    ctx: typer.Context,
    pull_zone_id: int = typer.Argument(..., help="Pull zone ID"),
    set_: list[str] = typer.Option([], "--set", help=SET_HELP),
) -> None:
    """Create a Shield zone for a pull zone."""
    _run(ctx, lambda c: c.create_shield_zone(pull_zone_id, **parse_set_pairs(set_)))


@zone_app.command(
    "update",
    epilog=examples(
        "bunnycdn shield zone update 7 --set wafEnabled=true",
        "bunnycdn shield zone update 7 --set wafExecutionMode=1 \\",
        "  --set requestBodyLoggingEnabled=false",
    ),
)
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


@waf_app.command(
    "review",
    epilog=examples(
        "bunnycdn shield waf review 7 920100 --action ignore",
        "bunnycdn shield waf review 7 920100 --action log-only",
        "bunnycdn shield waf review 7 920100 --action 2   # disable-rule",
    ),
)
def waf_review(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    rule_id: str = typer.Argument(
        ..., help="Triggered rule ID, as listed by `shield waf triggered`"
    ),
    action: str = typer.Option(
        ...,
        "--action",
        help="What to do with the rule: ignore (0), log-only (1) or disable-rule (2)",
    ),
) -> None:
    """Review a triggered WAF rule.

    Choose a decision for a rule listed by `shield waf triggered`: ignore
    the trigger, keep the rule but only log matches, or disable the rule.
    """
    code = _review_action(action)
    _run(ctx, lambda c: c.review_triggered_waf_rule(zone_id, rule_id, code))


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


@custom_rule_app.command(
    "create",
    epilog=examples(
        "bunnycdn shield waf custom-rule create 7 \\",
        "  --set ruleName=block-admin \\",
        "  --set ruleDescription='Block /admin' \\",
        '  --set ruleConfiguration=\'{"value":"/admin"}\'',
    ),
)
def custom_rule_create(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Create a custom WAF rule (e.g. --set ruleName=x --set ruleConfiguration='{...}')."""
    _run(ctx, lambda c: c.create_custom_waf_rule(zone_id, **parse_set_pairs(set_)))


@custom_rule_app.command(
    "update",
    epilog=examples(
        "bunnycdn shield waf custom-rule update 99 --set ruleName=new-name",
        "bunnycdn shield waf custom-rule update 99 \\",
        "  --set ruleConfiguration='{\"isNegated\":true}'",
    ),
)
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


@rate_limit_app.command(
    "create",
    epilog=examples(
        "bunnycdn shield rate-limit create 7 --set ruleName=api-limit \\",
        "  --set ruleConfiguration='{\"requestCount\":100}'",
    ),
)
def rate_limit_create(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Create a rate limit."""
    _run(ctx, lambda c: c.create_rate_limit(zone_id, **parse_set_pairs(set_)))


@rate_limit_app.command(
    "update",
    epilog=examples(
        "bunnycdn shield rate-limit update 55 --set ruleName=api-limit-2",
        "bunnycdn shield rate-limit update 55 \\",
        "  --set ruleConfiguration='{\"requestCount\":200}'",
    ),
)
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


@access_list_app.command(
    "create",
    epilog=examples(
        "bunnycdn shield access-list create 7 --set name=office \\",
        "  --set description='Office IPs'",
    ),
)
def access_list_create(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Create a custom access list."""
    _run(ctx, lambda c: c.create_access_list(zone_id, **parse_set_pairs(set_)))


@access_list_app.command(
    "update",
    epilog=examples(
        "bunnycdn shield access-list update 7 31 --set name=office-vpn",
    ),
)
def access_list_update(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    id: int = typer.Argument(..., help="Access list ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Update a custom access list."""
    _run(ctx, lambda c: c.update_access_list(zone_id, id, **parse_set_pairs(set_)))


@access_list_app.command(
    "configure",
    epilog=examples(
        "bunnycdn shield access-list configure 7 31 --set isEnabled=true",
        "bunnycdn shield access-list configure 7 31 --set action=1",
    ),
)
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


@bot_app.command(
    "update",
    epilog=examples(
        "bunnycdn shield bot-detection update 7 --set executionMode=1",
    ),
)
def bot_update(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Update bot detection configuration."""
    _run(ctx, lambda c: c.update_bot_detection(zone_id, **parse_set_pairs(set_)))


# --- event-log / metrics ----------------------------------------------------


@event_log_app.command(
    "get",
    epilog=examples(
        "bunnycdn shield event-log get 7 today _",
        "bunnycdn shield event-log get 7 10-15-2026 _",
    ),
)
def event_log_get(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    date: str = typer.Argument(..., help=f"Day: {WHEN_FORMATS}, or MM-dd-yyyy"),
    continuation_token: str = typer.Argument(
        ...,
        help="Continuation token from the previous response (first page: try _)",
    ),
) -> None:
    """Get event logs for a date.

    DATE may also be the API's own MM-dd-yyyy. Pass the continuation token
    from the previous response to page on.
    """
    if not re.fullmatch(r"\d{2}-\d{2}-\d{4}", date):  # the API's own MM-dd-yyyy passes through
        date = when(date, hint="DATE").strftime("%m-%d-%Y")
    _run(ctx, lambda c: c.get_event_logs(zone_id, date, continuation_token), raw=True)


@event_log_app.command(
    "search",
    epilog=examples(
        "bunnycdn shield event-log search 7 --set query=blocked",
        "bunnycdn shield event-log search 7 --set pageSize=50 --set page=1",
    ),
)
def event_log_search(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="Shield zone ID"),
    set_: list[str] = SetOpt,
) -> None:
    """Search event logs.

    Body fields include query, page, pageSize, groupBy and buckets. `from`
    and `to` are passed through unchanged; the API does not document their
    units.
    """
    _run(ctx, lambda c: c.search_event_logs(zone_id, **parse_set_pairs(set_)), raw=True)


@shield_app.command("metrics")
def metrics(ctx: typer.Context, zone_id: int = typer.Argument(..., help="Shield zone ID")) -> None:
    """Show the metrics overview for a Shield zone."""
    _run(ctx, lambda c: c.get_metrics_overview(zone_id))
