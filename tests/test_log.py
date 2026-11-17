"""Tests for SDK debug logging: redaction and failed-request events."""

from __future__ import annotations

import logging
from unittest.mock import patch

import httpx2
import pytest

from bunny_cdn_sdk._exceptions import BunnyConnectionError, BunnyServerError
from bunny_cdn_sdk._log import REDACTED, redact
from tests.conftest import make_base_client
from tests.test_retry import _client_with_retry


def test_redact_secret_fields_headers_and_query_params() -> None:
    value = {
        "AccessKey": "k1",
        "Name": "zone",
        "Password": "p",
        "ReadOnlyPassword": None,  # nothing to hide
        "Nested": [{"ZoneSecurityKey": "s", "Id": 1}],
        "url": "https://x/a?token=t&page=2&api_key=k2#f",
    }
    assert redact(value) == {
        "AccessKey": REDACTED,
        "Name": "zone",
        "Password": REDACTED,
        "ReadOnlyPassword": None,
        "Nested": [{"ZoneSecurityKey": REDACTED, "Id": 1}],
        "url": f"https://x/a?token={REDACTED}&page=2&api_key={REDACTED}#f",
    }


def test_failed_request_logs_redacted_context(caplog: pytest.LogCaptureFixture) -> None:
    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(500, json={"Message": "boom", "Password": "leaked"})

    client = make_base_client(handler)
    with caplog.at_level(logging.DEBUG, logger="bunny_cdn_sdk"), pytest.raises(BunnyServerError):
        client._request("POST", "https://api.test/zone?token=t", json={"Password": "secret"})

    text = caplog.text
    assert "event='request_failed'" in text
    assert "status=500" in text
    assert "'Message': 'boom'" in text
    for secret in ("test_api_key", "secret", "leaked", "token=t"):
        assert secret not in text


def test_connection_error_logged(caplog: pytest.LogCaptureFixture) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    client = make_base_client(handler)
    with (
        caplog.at_level(logging.DEBUG, logger="bunny_cdn_sdk"),
        pytest.raises(BunnyConnectionError),
    ):
        client._request("GET", "https://api.test/x")
    assert "event='request_error'" in caplog.text
    assert "refused" in caplog.text


def test_no_debug_events_when_not_enabled(caplog: pytest.LogCaptureFixture) -> None:
    client = make_base_client(lambda _r: httpx2.Response(500))
    with caplog.at_level(logging.INFO, logger="bunny_cdn_sdk"), pytest.raises(BunnyServerError):
        client._request("GET", "https://api.test/x")
    assert caplog.records == []


def test_retry_attempts_logged(caplog: pytest.LogCaptureFixture) -> None:
    responses = iter([httpx2.Response(503), httpx2.Response(200, json={})])
    client = _client_with_retry(lambda _r: next(responses), max_retries=2)
    with (
        caplog.at_level(logging.DEBUG, logger="bunny_cdn_sdk"),
        patch("time.sleep"),
    ):
        client._request("GET", "https://api.test/x")
    assert "event='request_retry'" in caplog.text
    assert "reason='HTTP 503'" in caplog.text
    assert "attempt=1" in caplog.text


def test_record_carries_redacted_fields_for_structured_handlers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = make_base_client(lambda _r: httpx2.Response(503, json={"Password": "leaked"}))
    with caplog.at_level(logging.DEBUG, logger="bunny_cdn_sdk"), pytest.raises(BunnyServerError):
        client._request("GET", "https://api.test/x")
    (record,) = caplog.records
    fields = record.bunny_event  # type: ignore[attr-defined]
    assert fields["event"] == "request_failed"
    assert fields["status"] == 503
    assert fields["request_headers"]["accesskey"] == REDACTED
    assert fields["response_body"] == {"Password": REDACTED}
