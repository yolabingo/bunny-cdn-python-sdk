"""Tests for the logs command."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from bunny_cdn_sdk._exceptions import BunnyAuthenticationError
from bunny_cdn_sdk.cli import app

_ROWS = [
    {
        "timestamp": f"t{i}",
        "statusCode": 200,
        "cacheStatus": "HIT",
        "countryCode": "US",
        "remoteIp": "1.1.1.1",
        "url": f"/u{i}",
    }
    for i in range(5)
]


def test_logs_table(runner) -> None:
    with patch("bunny_cdn_sdk.logs.LoggingClient") as mc:
        mc.return_value.iter_logs.return_value = iter(_ROWS)
        result = runner.invoke(app, ["--api-key", "k", "logs", "7"])
    assert result.exit_code == 0
    assert "/u0" in result.output
    mc.return_value.iter_logs.assert_called_once_with(7, limit=100)


def test_logs_json(runner) -> None:
    with patch("bunny_cdn_sdk.logs.LoggingClient") as mc:
        mc.return_value.iter_logs.return_value = iter(_ROWS)
        result = runner.invoke(app, ["--api-key", "k", "--output-format", "json", "logs", "7"])
    assert result.exit_code == 0
    assert json.loads(result.output) == _ROWS


def test_logs_option_mapping(runner) -> None:
    with patch("bunny_cdn_sdk.logs.LoggingClient") as mc:
        mc.return_value.iter_logs.return_value = iter([])
        result = runner.invoke(
            app,
            [
                "--api-key", "k", "logs", "7",
                "--from", "2026-01-01", "--to", "2026-01-02", "--status", "200,5xx",
                "--cache-status", "HIT", "--country", "US", "--search", "x", "--order", "asc",
                "--limit", "5000",
            ],
        )  # fmt: skip
    assert result.exit_code == 0
    mc.return_value.iter_logs.assert_called_once_with(
        7, limit=1000, **{"from": "2026-01-01", "to": "2026-01-02", "status": "200,5xx",
                          "cacheStatus": "HIT", "country": "US", "search": "x", "order": "asc"},
    )  # fmt: skip


def test_logs_limit_truncates(runner) -> None:
    with patch("bunny_cdn_sdk.logs.LoggingClient") as mc:
        mc.return_value.iter_logs.return_value = iter(_ROWS)
        result = runner.invoke(
            app, ["--api-key", "k", "--output-format", "json", "logs", "7", "--limit", "2"]
        )
    assert result.exit_code == 0
    assert len(json.loads(result.output)) == 2


def test_logs_sdk_error(runner) -> None:
    with patch("bunny_cdn_sdk.logs.LoggingClient") as mc:
        mc.return_value.iter_logs.side_effect = BunnyAuthenticationError(
            status_code=401, message="bad", response=MagicMock()
        )
        result = runner.invoke(app, ["--api-key", "k", "logs", "7"])
    assert result.exit_code == 1


def test_logs_missing_auth(runner) -> None:
    result = runner.invoke(app, ["logs", "7"])
    assert result.exit_code == 1
