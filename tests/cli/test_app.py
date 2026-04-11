"""Tests for CLI scaffold — app, help, auth wiring, sdk_errors(), output helpers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import typer

from bunny_cdn_sdk._exceptions import (
    BunnyAPIError,
    BunnyAuthenticationError,
    BunnyConnectionError,
    BunnyNotFoundError,
    BunnyRateLimitError,
    BunnyServerError,
    BunnyTimeoutError,
)
from bunny_cdn_sdk.cli import app
from bunny_cdn_sdk.cli._output import _cell, output_result, sdk_errors


# ---------------------------------------------------------------------------
# App — help and no-args
# ---------------------------------------------------------------------------


def test_help_exits_zero(runner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_help_contains_bunny(runner) -> None:
    result = runner.invoke(app, ["--help"])
    assert "bunny" in result.output.lower()


def test_no_args_shows_help(runner) -> None:
    # no_args_is_help=True — Typer shows help and exits 2 in CliRunner context
    result = runner.invoke(app, [])
    assert result.exit_code in (0, 2)
    assert "usage" in result.output.lower() or "bunny" in result.output.lower()


# ---------------------------------------------------------------------------
# Auth options visible in --help
# ---------------------------------------------------------------------------


def test_help_shows_api_key_option(runner) -> None:
    result = runner.invoke(app, ["--help"])
    assert "--api-key" in result.output
    assert "BUNNY_API_KEY" in result.output


def test_help_shows_storage_key_option(runner) -> None:
    result = runner.invoke(app, ["--help"])
    assert "--storage-key" in result.output
    assert "BUNNY_STORAGE_KEY" in result.output


def test_help_shows_zone_name_option(runner) -> None:
    result = runner.invoke(app, ["--help"])
    assert "--zone-name" in result.output
    assert "BUNNY_STORAGE_ZONE" in result.output


def test_help_shows_region_option(runner) -> None:
    result = runner.invoke(app, ["--help"])
    assert "--region" in result.output
    assert "BUNNY_STORAGE_REGION" in result.output


def test_help_shows_json_flag(runner) -> None:
    result = runner.invoke(app, ["--help"])
    assert "--json" in result.output


# ---------------------------------------------------------------------------
# sdk_errors() — exception-to-exit-code mapping
# ---------------------------------------------------------------------------


def _mock_exc(cls: type, status_code: int = 400, message: str = "test error") -> BunnyAPIError:
    """Helper: create an API exception with a mock response."""
    return cls(status_code=status_code, message=message, response=MagicMock())


def test_sdk_errors_catches_authentication_error() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        with sdk_errors():
            raise _mock_exc(BunnyAuthenticationError, 401, "Unauthorized")
    assert exc_info.value.exit_code == 1


def test_sdk_errors_catches_not_found_error() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        with sdk_errors():
            raise _mock_exc(BunnyNotFoundError, 404, "Zone not found")
    assert exc_info.value.exit_code == 1


def test_sdk_errors_catches_rate_limit_error() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        with sdk_errors():
            raise _mock_exc(BunnyRateLimitError, 429, "Too Many Requests")
    assert exc_info.value.exit_code == 1


def test_sdk_errors_catches_server_error() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        with sdk_errors():
            raise _mock_exc(BunnyServerError, 500, "Internal Server Error")
    assert exc_info.value.exit_code == 1


def test_sdk_errors_catches_api_error() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        with sdk_errors():
            raise _mock_exc(BunnyAPIError, 422, "Unprocessable Entity")
    assert exc_info.value.exit_code == 1


def test_sdk_errors_catches_connection_error() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        with sdk_errors():
            raise BunnyConnectionError("connection refused")
    assert exc_info.value.exit_code == 1


def test_sdk_errors_catches_timeout_error() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        with sdk_errors():
            raise BunnyTimeoutError("timed out")
    assert exc_info.value.exit_code == 1


def test_sdk_errors_catches_value_error() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        with sdk_errors():
            raise ValueError("bad argument")
    assert exc_info.value.exit_code == 1


def test_sdk_errors_passes_through_success() -> None:
    # No exception raised — context manager should not interfere
    with sdk_errors():
        result = 1 + 1
    assert result == 2


# ---------------------------------------------------------------------------
# output_result()
# ---------------------------------------------------------------------------


def test_output_result_json_mode_valid_json(capsys) -> None:
    output_result({"key": "val", "num": 42}, json_mode=True)
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["key"] == "val"
    assert parsed["num"] == 42


def test_output_result_json_mode_list(capsys) -> None:
    output_result([{"id": 1}, {"id": 2}], json_mode=True)
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert len(parsed) == 2


def test_output_result_plain_mode(capsys) -> None:
    output_result("hello world", json_mode=False)
    captured = capsys.readouterr()
    assert "hello world" in captured.out


# ---------------------------------------------------------------------------
# _cell()
# ---------------------------------------------------------------------------


def test_cell_none_returns_empty_string() -> None:
    assert _cell(None) == ""


def test_cell_dict_formats_key_value() -> None:
    assert _cell({"a": 1}) == "a=1"


def test_cell_list_shows_item_count() -> None:
    assert _cell([1, 2, 3]) == "[3 items]"


def test_cell_string_passthrough() -> None:
    assert _cell("hello") == "hello"


def test_cell_int_converts_to_string() -> None:
    assert _cell(42) == "42"
