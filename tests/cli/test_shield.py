"""Tests for shield CLI commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from bunny_cdn_sdk._exceptions import BunnyAuthenticationError
from bunny_cdn_sdk.cli import app

ROW = {
    "id": 1,
    "shieldZoneId": 1,
    "pullZoneId": 5,
    "ruleName": "needle",
    "name": "needle",
    "wafExecutionMode": "needle",
}

# (args, client method, expected positional args, iter_* method?)
CASES = [
    ("zone list", "iter_shield_zones", [], True),
    ("zone get 1", "get_shield_zone", [1], False),
    ("zone get-by-pull-zone 5", "get_shield_zone_by_pull_zone", [5], False),
    ("zone create 5 --set wafEnabled=true", "create_shield_zone", [5], False),
    ("zone update 1 --set wafEnabled=false", "update_shield_zone", [1], False),
    ("waf rules 1", "list_waf_rules", [1], False),
    ("waf profiles", "list_waf_profiles", [], False),
    ("waf enums", "get_waf_enums", [], False),
    ("waf engine-config", "get_waf_engine_config", [], False),
    ("waf triggered 1", "list_triggered_waf_rules", [1], False),
    ("waf review 1 r1 --action 2", "review_triggered_waf_rule", [1, "r1", 2], False),
    ("waf custom-rule list 1", "iter_custom_waf_rules", [1], True),
    ("waf custom-rule get 3", "get_custom_waf_rule", [3], False),
    ("waf custom-rule create 1 --set ruleName=x", "create_custom_waf_rule", [1], False),
    ("waf custom-rule update 3 --set ruleName=x", "update_custom_waf_rule", [3], False),
    ("rate-limit list 1", "iter_rate_limits", [1], True),
    ("rate-limit get 3", "get_rate_limit", [3], False),
    ("rate-limit create 1 --set ruleName=x", "create_rate_limit", [1], False),
    ("rate-limit update 3 --set ruleName=x", "update_rate_limit", [3], False),
    ("access-list list 1", "list_access_lists", [1], False),
    ("access-list get 1 4", "get_access_list", [1, 4], False),
    ("access-list create 1 --set name=x", "create_access_list", [1], False),
    ("access-list update 1 4 --set name=x", "update_access_list", [1, 4], False),
    (
        "access-list configure 1 4 --set isEnabled=true",
        "update_access_list_configuration",
        [1, 4],
        False,
    ),
    ("bot-detection get 1", "get_bot_detection", [1], False),
    ("bot-detection update 1 --set executionMode=1", "update_bot_detection", [1], False),
    ("event-log get 1 01-02-2026 tok", "get_event_logs", [1, "01-02-2026", "tok"], False),
    ("event-log search 1 --set a=1", "search_event_logs", [1], False),
    ("metrics 1", "get_metrics_overview", [1], False),
]

DELETES = [
    ("waf custom-rule delete 3", "delete_custom_waf_rule", [3]),
    ("rate-limit delete 3", "delete_rate_limit", [3]),
    ("access-list delete 1 4", "delete_access_list", [1, 4]),
]


def _exc() -> BunnyAuthenticationError:
    return BunnyAuthenticationError(status_code=401, message="err", response=MagicMock())


def _invoke(runner, args: str, *, json_mode: bool = False, key: bool = True, stdin=None):
    argv = (["--api-key", "k"] if key else []) + (["--json"] if json_mode else [])
    return runner.invoke(app, [*argv, "shield", *args.split()], input=stdin)


@pytest.mark.parametrize(("args", "method", "pos", "is_iter"), CASES)
def test_success(runner, args, method, pos, is_iter) -> None:
    with patch("bunny_cdn_sdk.shield.ShieldClient") as M:
        c = M.return_value
        getattr(c, method).return_value = iter([ROW]) if is_iter else {"data": ROW}
        result = _invoke(runner, args)
    assert result.exit_code == 0, result.output
    assert M.call_args.kwargs == {"api_key": "k"}
    assert getattr(c, method).call_args.args == tuple(pos)
    assert "needle" in result.output


@pytest.mark.parametrize(("args", "method", "pos", "is_iter"), CASES)
def test_error(runner, args, method, pos, is_iter) -> None:
    with patch("bunny_cdn_sdk.shield.ShieldClient") as M:
        getattr(M.return_value, method).side_effect = _exc()
        assert _invoke(runner, args).exit_code == 1


@pytest.mark.parametrize(("args", "method", "pos", "is_iter"), CASES)
def test_missing_auth(runner, args, method, pos, is_iter) -> None:
    assert _invoke(runner, args, key=False).exit_code == 1


@pytest.mark.parametrize(("args", "method", "pos", "is_iter"), CASES[:4])
def test_json(runner, args, method, pos, is_iter) -> None:
    with patch("bunny_cdn_sdk.shield.ShieldClient") as M:
        getattr(M.return_value, method).return_value = iter([ROW]) if is_iter else {"data": ROW}
        result = _invoke(runner, args, json_mode=True)
    assert result.exit_code == 0
    assert json.loads(result.output) in ([ROW], ROW)


def test_set_values_json_parsed(runner) -> None:
    with patch("bunny_cdn_sdk.shield.ShieldClient") as M:
        c = M.return_value
        c.create_custom_waf_rule.return_value = {"data": ROW}
        result = _invoke(
            runner, 'waf custom-rule create 1 --set ruleName=x --set ruleConfiguration={"a":1}'
        )
    assert result.exit_code == 0
    assert c.create_custom_waf_rule.call_args.kwargs == {
        "ruleName": "x",
        "ruleConfiguration": {"a": 1},
    }


@pytest.mark.parametrize(("args", "method", "pos"), DELETES)
def test_delete(runner, args, method, pos) -> None:
    with patch("bunny_cdn_sdk.shield.ShieldClient") as M:
        result = _invoke(runner, args + " --yes")
    assert result.exit_code == 0
    assert getattr(M.return_value, method).call_args.args == tuple(pos)
    assert "Deleted" in result.output


@pytest.mark.parametrize(("args", "method", "pos"), DELETES)
def test_delete_declined(runner, args, method, pos) -> None:
    with patch("bunny_cdn_sdk.shield.ShieldClient") as M:
        result = _invoke(runner, args, stdin="n\n")
    assert result.exit_code == 1
    getattr(M.return_value, method).assert_not_called()


@pytest.mark.parametrize(("args", "method", "pos"), DELETES)
def test_delete_error(runner, args, method, pos) -> None:
    with patch("bunny_cdn_sdk.shield.ShieldClient") as M:
        getattr(M.return_value, method).side_effect = _exc()
        assert _invoke(runner, args + " -y").exit_code == 1
