"""Structured (--output-format json) error output: code, message, status, retryable on stderr."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from bunny_cdn_sdk._exceptions import (
    BunnyAPIError,
    BunnyAuthenticationError,
    BunnyConnectionError,
    BunnyNotFoundError,
    BunnyRateLimitError,
    BunnySDKError,
    BunnyServerError,
    BunnyTimeoutError,
)
from bunny_cdn_sdk.cli import app


def _api(cls, status):
    return cls(status, "boom", MagicMock())


@pytest.mark.parametrize(
    ("exc", "code", "status", "retryable"),
    [
        (_api(BunnyAuthenticationError, 401), "authentication_failed", 401, False),
        (_api(BunnyNotFoundError, 404), "not_found", 404, False),
        (_api(BunnyRateLimitError, 429), "rate_limited", 429, True),
        (_api(BunnyServerError, 503), "server_error", 503, True),
        (_api(BunnyAPIError, 400), "api_error", 400, False),
        (BunnyTimeoutError("slow"), "timeout", None, True),
        (BunnyConnectionError("down"), "connection_error", None, True),
        (BunnySDKError("odd"), "sdk_error", None, False),
        (ValueError("bad"), "invalid_argument", None, False),
    ],
)
def test_json_error(runner, exc, code, status, retryable) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        M.return_value.get_contract.side_effect = exc
        result = runner.invoke(
            app, ["--output-format", "json", "--api-key", "k", "partner", "contract"]
        )
    assert result.exit_code == 1
    assert result.stdout == ""
    err = json.loads(result.stderr)["error"]
    assert err["code"] == code
    assert err["status"] == status
    assert err["retryable"] is retryable
    assert err["message"]


def test_json_missing_key(runner) -> None:
    result = runner.invoke(app, ["--output-format", "json", "partner", "contract"])
    assert result.exit_code == 1
    err = json.loads(result.stderr)["error"]
    assert err == {
        "code": "missing_api_key",
        "message": err["message"],
        "status": None,
        "retryable": False,
    }
    assert "BUNNY_PARTNER_API_KEY" in err["message"]


def test_plain_error_without_json(runner) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        M.return_value.get_contract.side_effect = _api(BunnyRateLimitError, 429)
        result = runner.invoke(app, ["--api-key", "k", "partner", "contract"])
    assert result.exit_code == 1
    assert "Rate limited" in result.stderr
    assert "{" not in result.stderr
