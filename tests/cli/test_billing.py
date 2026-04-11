"""Tests for top-level billing command (UTIL-03)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from bunny_cdn_sdk._exceptions import BunnyAPIError, BunnyAuthenticationError
from bunny_cdn_sdk.cli import app

_BILLING = {
    "Balance": 12.34,
    "ThisMonthCharges": 5.67,
    "UnpaidInvoicesAmount": 0.0,
    "MonthlyChargesStorage": 1.00,
    "MonthlyChargesEUTraffic": 2.00,
    "MonthlyChargesUSTraffic": 1.50,
    "MonthlyChargesASIATraffic": 0.75,
    "MonthlyChargesAFRICATraffic": 0.25,
}


def _mock_exc(cls: type, status_code: int = 400, message: str = "err") -> object:
    return cls(status_code=status_code, message=message, response=MagicMock())


# ---------------------------------------------------------------------------
# billing — success path
# ---------------------------------------------------------------------------


def test_billing_success(runner) -> None:
    """billing displays key billing fields in a table."""
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_billing.return_value = _BILLING
        result = runner.invoke(app, ["--api-key", "k", "billing"])
    assert result.exit_code == 0
    assert "Balance" in result.output
    assert "12.34" in result.output


def test_billing_shows_key_fields(runner) -> None:
    """billing --json output includes all curated billing columns as keys."""
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_billing.return_value = _BILLING
        result = runner.invoke(app, ["--api-key", "k", "--json", "billing"])
    parsed = json.loads(result.output)
    for field_name in [
        "Balance",
        "ThisMonthCharges",
        "UnpaidInvoicesAmount",
        "MonthlyChargesStorage",
    ]:
        assert field_name in parsed, f"Expected '{field_name}' in JSON output"


def test_billing_json_output(runner) -> None:
    """billing --json outputs the raw billing dict."""
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_billing.return_value = _BILLING
        result = runner.invoke(app, ["--api-key", "k", "--json", "billing"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, dict)
    assert parsed["Balance"] == 12.34


def test_billing_missing_auth(runner) -> None:
    """billing without --api-key exits 1 with actionable message."""
    result = runner.invoke(app, ["billing"])
    assert result.exit_code == 1
    assert "Missing API key" in result.output


def test_billing_api_error(runner) -> None:
    """billing with API error exits 1."""
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_billing.side_effect = _mock_exc(
            BunnyAuthenticationError, 401
        )
        result = runner.invoke(app, ["--api-key", "bad", "billing"])
    assert result.exit_code == 1


def test_billing_calls_get_billing(runner) -> None:
    """billing calls get_billing() exactly once."""
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mc = MockClient.return_value
        mc.get_billing.return_value = _BILLING
        runner.invoke(app, ["--api-key", "k", "billing"])
    mc.get_billing.assert_called_once_with()
