"""Tests for pull-zone CLI commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from bunny_cdn_sdk._exceptions import BunnyAPIError, BunnyAuthenticationError, BunnyNotFoundError
from bunny_cdn_sdk.cli import app

PULL_ZONE = {"Id": 1, "Name": "my-zone", "OriginUrl": "https://origin.example.com", "Enabled": True}


def _mock_exc(cls: type, status_code: int = 400, message: str = "err") -> object:
    return cls(status_code=status_code, message=message, response=MagicMock())


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_pull_zone_list_success(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.iter_pull_zones.return_value = iter([PULL_ZONE])
        result = runner.invoke(app, ["--api-key", "k", "pull-zone", "list"])
    assert result.exit_code == 0
    assert "my-zone" in result.output


def test_pull_zone_list_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.iter_pull_zones.side_effect = _mock_exc(BunnyAuthenticationError, 401)
        result = runner.invoke(app, ["--api-key", "k", "pull-zone", "list"])
    assert result.exit_code == 1


def test_pull_zone_list_json(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.iter_pull_zones.return_value = iter([PULL_ZONE])
        result = runner.invoke(
            app, ["--api-key", "k", "--output-format", "json", "pull-zone", "list"]
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["Name"] == "my-zone"


def test_pull_zone_list_missing_auth(runner) -> None:
    result = runner.invoke(app, ["pull-zone", "list"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_pull_zone_get_success(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_pull_zone.return_value = PULL_ZONE
        result = runner.invoke(app, ["--api-key", "k", "pull-zone", "get", "1"])
    assert result.exit_code == 0
    assert "my-zone" in result.output


def test_pull_zone_get_not_found(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_pull_zone.side_effect = _mock_exc(BunnyNotFoundError, 404)
        result = runner.invoke(app, ["--api-key", "k", "pull-zone", "get", "999"])
    assert result.exit_code == 1


def test_pull_zone_get_json(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_pull_zone.return_value = PULL_ZONE
        result = runner.invoke(
            app, ["--api-key", "k", "--output-format", "json", "pull-zone", "get", "1"]
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Id"] == 1


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_pull_zone_create_success(runner) -> None:
    created = {**PULL_ZONE, "Name": "new-zone"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.create_pull_zone.return_value = created
        result = runner.invoke(
            app,
            [
                "--api-key",
                "k",
                "pull-zone",
                "create",
                "--name",
                "new-zone",
                "--origin-url",
                "https://o.example.com",
            ],
        )
    assert result.exit_code == 0
    assert "new-zone" in result.output
    MockClient.return_value.create_pull_zone.assert_called_once_with(
        Name="new-zone", OriginUrl="https://o.example.com"
    )


def test_pull_zone_create_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.create_pull_zone.side_effect = _mock_exc(BunnyAPIError, 422)
        result = runner.invoke(
            app,
            [
                "--api-key",
                "k",
                "pull-zone",
                "create",
                "--name",
                "z",
                "--origin-url",
                "https://o.example.com",
            ],
        )
    assert result.exit_code == 1


def test_pull_zone_create_json(runner) -> None:
    created = {**PULL_ZONE, "Name": "new-zone"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.create_pull_zone.return_value = created
        result = runner.invoke(
            app,
            [
                "--api-key",
                "k",
                "--output-format",
                "json",
                "pull-zone",
                "create",
                "--name",
                "new-zone",
                "--origin-url",
                "https://o.example.com",
            ],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Name"] == "new-zone"
    MockClient.return_value.create_pull_zone.assert_called_once_with(
        Name="new-zone", OriginUrl="https://o.example.com"
    )


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_pull_zone_delete_with_yes(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_pull_zone.return_value = PULL_ZONE
        MockClient.return_value.delete_pull_zone.return_value = {}
        result = runner.invoke(app, ["--api-key", "k", "pull-zone", "delete", "1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted pull zone 1" in result.output
    MockClient.return_value.delete_pull_zone.assert_called_once_with(1)


def test_pull_zone_delete_prompt_confirmed(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_pull_zone.return_value = PULL_ZONE
        MockClient.return_value.delete_pull_zone.return_value = {}
        result = runner.invoke(app, ["--api-key", "k", "pull-zone", "delete", "1"], input="y\n")
    assert result.exit_code == 0
    MockClient.return_value.delete_pull_zone.assert_called_once_with(1)


def test_pull_zone_delete_prompt_aborted(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_pull_zone.return_value = PULL_ZONE
        result = runner.invoke(app, ["--api-key", "k", "pull-zone", "delete", "1"], input="n\n")
    assert result.exit_code != 0


def test_pull_zone_delete_not_found(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_pull_zone.side_effect = _mock_exc(BunnyNotFoundError, 404)
        result = runner.invoke(app, ["--api-key", "k", "pull-zone", "delete", "999", "--yes"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# purge
# ---------------------------------------------------------------------------


def test_pull_zone_purge_success(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.purge_pull_zone_cache.return_value = {}
        result = runner.invoke(app, ["--api-key", "k", "pull-zone", "purge", "1"])
    assert result.exit_code == 0
    assert "Purged cache" in result.output or "purge" in result.output.lower()
    MockClient.return_value.purge_pull_zone_cache.assert_called_once_with(1)


def test_pull_zone_purge_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.purge_pull_zone_cache.side_effect = _mock_exc(
            BunnyNotFoundError, 404
        )
        result = runner.invoke(app, ["--api-key", "k", "pull-zone", "purge", "999"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_pull_zone_update_success_shows_diff(runner) -> None:
    before = {**PULL_ZONE, "OriginUrl": "https://old.example.com"}
    after = {**PULL_ZONE, "OriginUrl": "https://new.example.com"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_pull_zone.return_value = before
        MockClient.return_value.update_pull_zone.return_value = after
        result = runner.invoke(
            app,
            [
                "--api-key",
                "k",
                "pull-zone",
                "update",
                "1",
                "--set",
                "OriginUrl=https://new.example.com",
            ],
        )
    assert result.exit_code == 0
    assert "OriginUrl" in result.output
    MockClient.return_value.update_pull_zone.assert_called_once_with(
        1, OriginUrl="https://new.example.com"
    )


def test_pull_zone_update_json(runner) -> None:
    after = {**PULL_ZONE, "OriginUrl": "https://new.example.com"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_pull_zone.return_value = PULL_ZONE
        MockClient.return_value.update_pull_zone.return_value = after
        result = runner.invoke(
            app,
            [
                "--api-key",
                "k",
                "--output-format",
                "json",
                "pull-zone",
                "update",
                "1",
                "--set",
                "OriginUrl=https://new.example.com",
            ],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["OriginUrl"] == "https://new.example.com"
    MockClient.return_value.update_pull_zone.assert_called_once_with(
        1, OriginUrl="https://new.example.com"
    )


def test_pull_zone_update_malformed_set(runner) -> None:
    result = runner.invoke(app, ["--api-key", "k", "pull-zone", "update", "1", "--set", "NOEQUALS"])
    assert result.exit_code == 1


def test_pull_zone_update_error_on_get(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_pull_zone.side_effect = _mock_exc(BunnyNotFoundError, 404)
        result = runner.invoke(
            app, ["--api-key", "k", "pull-zone", "update", "1", "--set", "Name=x"]
        )
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# edge-rule
# ---------------------------------------------------------------------------

RULE = {"Guid": "g-1", "Description": "block bots", "ActionType": 0, "Enabled": True}


def _edge(runner, *args: str, setup=None):
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        if setup:
            setup(MockClient.return_value)
        result = runner.invoke(app, ["--api-key", "k", *args])
    return result, MockClient.return_value


def test_edge_rule_list(runner) -> None:
    def setup(c):
        c.get_pull_zone.return_value = {**PULL_ZONE, "EdgeRules": [RULE]}

    result, _ = _edge(runner, "pull-zone", "edge-rule", "list", "1", setup=setup)
    assert result.exit_code == 0
    assert "block bots" in result.output


def test_edge_rule_list_json_empty(runner) -> None:
    def setup(c):
        c.get_pull_zone.return_value = PULL_ZONE

    result, _ = _edge(
        runner, "--output-format", "json", "pull-zone", "edge-rule", "list", "1", setup=setup
    )
    assert result.exit_code == 0
    assert json.loads(result.output) == []


def test_edge_rule_list_error(runner) -> None:
    def setup(c):
        c.get_pull_zone.side_effect = _mock_exc(BunnyNotFoundError, 404)

    result, _ = _edge(runner, "pull-zone", "edge-rule", "list", "1", setup=setup)
    assert result.exit_code == 1


def test_edge_rule_set(runner) -> None:
    def setup(c):
        c.add_or_update_edge_rule.return_value = RULE

    result, c = _edge(
        runner,
        "--output-format",
        "json",
        "pull-zone",
        "edge-rule",
        "set",
        "1",
        "--set",
        "Guid=g-1",
        "--set",
        "Enabled=false",
        setup=setup,
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["Guid"] == "g-1"
    c.add_or_update_edge_rule.assert_called_once_with(1, Guid="g-1", Enabled=False)


def test_edge_rule_set_error(runner) -> None:
    def setup(c):
        c.add_or_update_edge_rule.side_effect = _mock_exc(BunnyAPIError, 400)

    result, _ = _edge(runner, "pull-zone", "edge-rule", "set", "1", "--set", "A=1", setup=setup)
    assert result.exit_code == 1


def test_edge_rule_delete_yes_and_abort(runner) -> None:
    result, c = _edge(runner, "pull-zone", "edge-rule", "delete", "1", "g-1", "--yes")
    assert result.exit_code == 0
    c.delete_edge_rule.assert_called_once_with(1, "g-1")
    result, c = _edge(runner, "pull-zone", "edge-rule", "delete", "1", "g-1")
    assert result.exit_code != 0  # no input -> confirm aborts
    c.delete_edge_rule.assert_not_called()


def test_edge_rule_delete_error(runner) -> None:
    def setup(c):
        c.delete_edge_rule.side_effect = _mock_exc(BunnyAPIError, 500)

    result, _ = _edge(runner, "pull-zone", "edge-rule", "delete", "1", "g", "-y", setup=setup)
    assert result.exit_code == 1


def test_edge_rule_enable_disable(runner) -> None:
    result, c = _edge(runner, "pull-zone", "edge-rule", "enable", "1", "g-1")
    assert result.exit_code == 0
    c.set_edge_rule_enabled.assert_called_once_with(1, "g-1", enabled=True)
    result, c = _edge(runner, "pull-zone", "edge-rule", "disable", "1", "g-1")
    assert result.exit_code == 0
    c.set_edge_rule_enabled.assert_called_once_with(1, "g-1", enabled=False)


def test_edge_rule_enable_error(runner) -> None:
    def setup(c):
        c.set_edge_rule_enabled.side_effect = _mock_exc(BunnyAPIError, 500)

    result, _ = _edge(runner, "pull-zone", "edge-rule", "enable", "1", "g", setup=setup)
    assert result.exit_code == 1


def test_edge_rule_missing_auth(runner) -> None:
    assert runner.invoke(app, ["pull-zone", "edge-rule", "list", "1"]).exit_code == 1
