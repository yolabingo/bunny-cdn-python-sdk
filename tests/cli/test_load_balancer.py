"""Tests for load-balancer CLI commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from bunny_cdn_sdk._exceptions import BunnyAPIError
from bunny_cdn_sdk.cli import app

LB = {"Id": 7, "Name": "my-lb", "Enabled": True}


def _run(runner, *args: str, **returns):
    """Invoke the CLI with a mocked CoreClient; kwargs set method return/side effects."""
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        client = MockClient.return_value
        for name, value in returns.items():
            m = getattr(client, name)
            if isinstance(value, Exception):
                m.side_effect = value
            else:
                m.return_value = value
        result = runner.invoke(app, ["--api-key", "k", *args])
    return result, client


ERR = BunnyAPIError(status_code=500, message="boom", response=MagicMock())


def test_list(runner) -> None:
    result, c = _run(runner, "load-balancer", "list", "--page", "2", list_load_balancers=[LB])
    assert result.exit_code == 0
    assert "my-lb" in result.output
    c.list_load_balancers.assert_called_once_with(page=2, count=50)


def test_list_json(runner) -> None:
    result, _ = _run(
        runner, "--output-format", "json", "load-balancer", "list", list_load_balancers=[LB]
    )
    assert json.loads(result.output)[0]["Name"] == "my-lb"


def test_get_and_json(runner) -> None:
    result, _ = _run(runner, "load-balancer", "get", "7", get_load_balancer=LB)
    assert result.exit_code == 0
    assert "my-lb" in result.output
    result, _ = _run(
        runner, "--output-format", "json", "load-balancer", "get", "7", get_load_balancer=LB
    )
    assert json.loads(result.output)["Id"] == 7


def test_create(runner) -> None:
    result, c = _run(
        runner,
        "--output-format",
        "json",
        "load-balancer",
        "create",
        "--name",
        "my-lb",
        "--set",
        "Enabled=true",
        create_load_balancer=LB,
    )
    assert result.exit_code == 0
    c.create_load_balancer.assert_called_once_with(Name="my-lb", Enabled=True)


def test_update(runner) -> None:
    result, c = _run(
        runner, "load-balancer", "update", "7", "--set", "Name=x", update_load_balancer=LB
    )
    assert result.exit_code == 0
    c.update_load_balancer.assert_called_once_with(7, Name="x")


def test_update_malformed_set(runner) -> None:
    result, _ = _run(runner, "load-balancer", "update", "7", "--set", "NOEQUALS")
    assert result.exit_code == 1


def test_delete_yes_and_abort(runner) -> None:
    result, c = _run(runner, "load-balancer", "delete", "7", "-y", get_load_balancer=LB)
    assert result.exit_code == 0
    c.delete_load_balancer.assert_called_once_with(7)
    result, c = _run(runner, "load-balancer", "delete", "7", get_load_balancer=LB)
    assert result.exit_code != 0
    c.delete_load_balancer.assert_not_called()


def test_stats_args(runner) -> None:
    result, c = _run(
        runner,
        "--output-format",
        "json",
        "load-balancer",
        "stats",
        "7",
        "--from",
        "2026-01-01",
        "--hourly",
        get_load_balancer_statistics={"Total": 1},
    )
    assert result.exit_code == 0
    assert json.loads(result.output) == {"Total": 1}
    c.get_load_balancer_statistics.assert_called_once_with(7, hourly=True, **{"from": "2026-01-01"})


def test_pull_zones_account_stats_usage(runner) -> None:
    result, c = _run(
        runner,
        "load-balancer",
        "pull-zones",
        "7",
        "--to",
        "2026-02-01",
        get_load_balancer_pull_zones={"A": 1},
    )
    assert result.exit_code == 0
    c.get_load_balancer_pull_zones.assert_called_once_with(7, to="2026-02-01")
    result, c = _run(
        runner, "load-balancer", "account-stats", get_load_balancer_account_statistics={"A": 1}
    )
    assert result.exit_code == 0
    c.get_load_balancer_account_statistics.assert_called_once_with()
    result, c = _run(
        runner,
        "load-balancer",
        "usage",
        "7",
        "--year",
        "2026",
        "--month",
        "3",
        get_load_balancer_usage={"A": 1},
    )
    assert result.exit_code == 0
    c.get_load_balancer_usage.assert_called_once_with(7, year=2026, month=3)


def test_origin_group_commands(runner) -> None:
    result, c = _run(
        runner,
        "load-balancer",
        "origin-group",
        "add",
        "7",
        "--set",
        "Name=g",
        add_origin_group={"Id": 1},
    )
    assert result.exit_code == 0
    c.add_origin_group.assert_called_once_with(7, Name="g")
    result, c = _run(
        runner,
        "load-balancer",
        "origin-group",
        "update",
        "7",
        "1",
        "--set",
        "Name=h",
        update_origin_group={"Id": 1},
    )
    assert result.exit_code == 0
    c.update_origin_group.assert_called_once_with(7, 1, Name="h")
    result, c = _run(runner, "load-balancer", "origin-group", "delete", "7", "1", "-y")
    assert result.exit_code == 0
    c.delete_origin_group.assert_called_once_with(7, 1)
    result, c = _run(runner, "load-balancer", "origin-group", "delete", "7", "1")
    assert result.exit_code != 0
    c.delete_origin_group.assert_not_called()


def test_origin_commands(runner) -> None:
    result, c = _run(
        runner,
        "--output-format",
        "json",
        "load-balancer",
        "origin",
        "add",
        "7",
        "1",
        "--set",
        "Address=a.com",
        add_origin={"Id": 2},
    )
    assert result.exit_code == 0
    c.add_origin.assert_called_once_with(7, 1, Address="a.com")
    result, c = _run(
        runner,
        "load-balancer",
        "origin",
        "update",
        "7",
        "1",
        "2",
        "--set",
        "Weight=5",
        update_origin={"Id": 2},
    )
    assert result.exit_code == 0
    c.update_origin.assert_called_once_with(7, 1, 2, Weight=5)
    result, c = _run(runner, "load-balancer", "origin", "delete", "7", "1", "2", "--yes")
    assert result.exit_code == 0
    c.delete_origin.assert_called_once_with(7, 1, 2)
    result, c = _run(runner, "load-balancer", "origin", "delete", "7", "1", "2")
    assert result.exit_code != 0
    c.delete_origin.assert_not_called()


@pytest.mark.parametrize(
    ("args", "method"),
    [
        (["list"], "list_load_balancers"),
        (["get", "7"], "get_load_balancer"),
        (["create", "--name", "n"], "create_load_balancer"),
        (["update", "7", "--set", "A=1"], "update_load_balancer"),
        (["delete", "7", "-y"], "get_load_balancer"),
        (["stats", "7"], "get_load_balancer_statistics"),
        (["pull-zones", "7"], "get_load_balancer_pull_zones"),
        (["account-stats"], "get_load_balancer_account_statistics"),
        (["usage", "7"], "get_load_balancer_usage"),
        (["origin-group", "add", "7"], "add_origin_group"),
        (["origin-group", "update", "7", "1", "--set", "A=1"], "update_origin_group"),
        (["origin-group", "delete", "7", "1", "-y"], "delete_origin_group"),
        (["origin", "add", "7", "1"], "add_origin"),
        (["origin", "update", "7", "1", "2", "--set", "A=1"], "update_origin"),
        (["origin", "delete", "7", "1", "2", "-y"], "delete_origin"),
    ],
)
def test_sdk_error_exits_1(runner, args: list[str], method: str) -> None:
    result, _ = _run(runner, "load-balancer", *args, **{method: ERR})
    assert result.exit_code == 1


@pytest.mark.parametrize(
    "args", [["list"], ["origin-group", "add", "7"], ["origin", "add", "7", "1"]]
)
def test_missing_auth(runner, args: list[str]) -> None:
    assert runner.invoke(app, ["load-balancer", *args]).exit_code == 1
