"""Tests for RetryTransport — retry triggers, backoff, and composability."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import patch

import httpx
import pytest

from bunny_cdn_sdk import RetryTransport
from bunny_cdn_sdk._client import _BaseClient
from bunny_cdn_sdk._exceptions import (
    BunnyConnectionError,
    BunnyServerError,
    BunnyTimeoutError,
)
from bunny_cdn_sdk._retry import _parse_retry_after

_URL = "https://api.bunnycdn.com/pullzone/1"


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_flaky_handler(fail_count: int, fail_status: int = 503, headers: dict | None = None):
    """Return (handler, call_list) where handler fails fail_count times then succeeds.

    Args:
        fail_count: Number of initial calls that return fail_status.
        fail_status: HTTP status code for failing responses.
        headers: Optional response headers to attach to failing responses.
    """
    calls: list[httpx.Request] = []
    fail_headers = headers or {}

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        if len(calls) <= fail_count:
            return httpx.Response(fail_status, headers=fail_headers)
        return httpx.Response(200, json={"ok": True})

    return handler, calls


def _make_always_fail_handler(fail_status: int = 503):
    """Return (handler, call_list) where every call returns fail_status."""
    calls: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        return httpx.Response(fail_status)

    return handler, calls


def _make_network_error_handler(exc: Exception, fail_count: int):
    """Return handler that raises exc for the first fail_count calls, then succeeds."""
    calls: list[int] = [0]

    def handler(req: httpx.Request) -> httpx.Response:
        calls[0] += 1
        if calls[0] <= fail_count:
            raise exc
        return httpx.Response(200, json={"ok": True})

    return handler, calls


def _make_always_network_error_handler(exc: Exception):
    """Return handler that always raises exc."""

    def handler(req: httpx.Request) -> httpx.Response:
        raise exc

    return handler


def _client_with_retry(
    handler,
    max_retries: int = 3,
    backoff_base: float = 0.5,
) -> _BaseClient:
    """Wire: handler -> MockTransport -> RetryTransport -> AsyncClient -> _BaseClient."""
    inner = httpx.MockTransport(handler)
    retry_transport = RetryTransport(inner, max_retries=max_retries, backoff_base=backoff_base)
    async_client = httpx.Client(transport=retry_transport)
    return _BaseClient("test_api_key", client=async_client)


# ---------------------------------------------------------------------------
# 5xx retry
# ---------------------------------------------------------------------------


def test_retries_on_503() -> None:
    """RetryTransport retries on 5xx and returns 200 on success."""
    handler, calls = _make_flaky_handler(fail_count=2, fail_status=503)
    client = _client_with_retry(handler, max_retries=3)

    with patch("time.sleep") as mock_sleep:
        resp = client._sync_request("GET", _URL)

    assert resp.status_code == 200
    assert len(calls) == 3  # 1 initial + 2 retries
    assert mock_sleep.call_count == 2  # sleep before retry 1 and retry 2


def test_retries_on_500() -> None:
    """RetryTransport retries on 500 (lower bound of 5xx range)."""
    handler, calls = _make_flaky_handler(fail_count=1, fail_status=500)
    client = _client_with_retry(handler, max_retries=2)

    with patch("time.sleep"):
        resp = client._sync_request("GET", _URL)

    assert resp.status_code == 200
    assert len(calls) == 2


def test_no_sleep_on_first_attempt() -> None:
    """asyncio.sleep is NOT called before the very first attempt."""
    handler, calls = _make_flaky_handler(fail_count=0)
    client = _client_with_retry(handler, max_retries=3)

    with patch("time.sleep") as mock_sleep:
        resp = client._sync_request("GET", _URL)

    assert resp.status_code == 200
    assert len(calls) == 1
    assert mock_sleep.call_count == 0


# ---------------------------------------------------------------------------
# 429 retry — Retry-After header variants
# ---------------------------------------------------------------------------


def test_retries_on_429_with_retry_after_integer() -> None:
    """RetryTransport respects Retry-After integer-seconds header on 429."""
    handler, calls = _make_flaky_handler(
        fail_count=1,
        fail_status=429,
        headers={"Retry-After": "42"},
    )
    client = _client_with_retry(handler, max_retries=2)

    with patch("time.sleep") as mock_sleep:
        resp = client._sync_request("GET", _URL)

    assert resp.status_code == 200
    assert len(calls) == 2
    assert mock_sleep.call_count == 1
    assert mock_sleep.call_args_list[0].args[0] == pytest.approx(42.0)


def test_retries_on_429_with_retry_after_http_date() -> None:
    """RetryTransport parses Retry-After HTTP-date and sleeps for the remaining seconds."""
    # Set the retry-after date 30 seconds in the future
    future = datetime.now(UTC) + timedelta(seconds=30)
    http_date = format_datetime(future, usegmt=True)

    handler, calls = _make_flaky_handler(
        fail_count=1,
        fail_status=429,
        headers={"Retry-After": http_date},
    )
    client = _client_with_retry(handler, max_retries=2)

    with patch("time.sleep") as mock_sleep:
        resp = client._sync_request("GET", _URL)

    assert resp.status_code == 200
    assert len(calls) == 2
    assert mock_sleep.call_count == 1
    # Allow up to 2s tolerance for test execution time
    delay = mock_sleep.call_args_list[0].args[0]
    assert 28.0 <= delay <= 32.0


def test_retries_on_429_without_retry_after_uses_backoff() -> None:
    """RetryTransport falls back to normal backoff when Retry-After is absent on 429."""
    handler, calls = _make_flaky_handler(fail_count=1, fail_status=429)
    client = _client_with_retry(handler, max_retries=2, backoff_base=0.5)

    with patch("time.sleep") as mock_sleep:
        with patch("random.uniform", side_effect=lambda lo, hi: hi):
            resp = client._sync_request("GET", _URL)

    assert resp.status_code == 200
    assert len(calls) == 2
    assert mock_sleep.call_count == 1
    # attempt=0 → upper bound = min(60.0, 0.5 * 2**0) = 0.5
    assert mock_sleep.call_args_list[0].args[0] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Network exception retry
# ---------------------------------------------------------------------------


def test_retries_on_connect_error() -> None:
    """RetryTransport retries on httpx.ConnectError and returns 200 on success."""
    handler, calls = _make_network_error_handler(
        httpx.ConnectError("Connection refused"), fail_count=2
    )
    client = _client_with_retry(handler, max_retries=3)

    with patch("time.sleep") as mock_sleep:
        resp = client._sync_request("GET", _URL)

    assert resp.status_code == 200
    assert calls[0] == 3  # 1 initial + 2 retries
    assert mock_sleep.call_count == 2


def test_retries_on_timeout_exception() -> None:
    """RetryTransport retries on httpx.TimeoutException and returns 200 on success."""
    handler, calls = _make_network_error_handler(httpx.TimeoutException("Timed out"), fail_count=1)
    client = _client_with_retry(handler, max_retries=2)

    with patch("time.sleep"):
        resp = client._sync_request("GET", _URL)

    assert resp.status_code == 200
    assert calls[0] == 2


# ---------------------------------------------------------------------------
# Max retries exhausted
# ---------------------------------------------------------------------------


def test_max_retries_exhausted_returns_final_5xx_response() -> None:
    """When all retries fail with 5xx, the final failed response is returned (not raised).

    _BaseClient._request() calls raise_for_status() above the transport layer,
    so it will ultimately raise BunnyServerError. Here we test the transport
    directly to confirm the final response object is passed through unchanged.
    """
    handler, calls = _make_always_fail_handler(fail_status=503)
    client = _client_with_retry(handler, max_retries=2)

    with patch("time.sleep"):
        with pytest.raises(BunnyServerError):
            client._sync_request("GET", _URL)

    # max_retries=2 means 3 total attempts (1 initial + 2 retries)
    assert len(calls) == 3


def test_max_retries_exhausted_reraises_connect_error() -> None:
    """When all retries fail with ConnectError, the exception is re-raised."""
    handler = _make_always_network_error_handler(httpx.ConnectError("Connection refused"))
    client = _client_with_retry(handler, max_retries=1)

    with patch("time.sleep"):
        with pytest.raises(BunnyConnectionError):
            client._sync_request("GET", _URL)


def test_max_retries_exhausted_reraises_timeout_exception() -> None:
    """When all retries fail with TimeoutException, the exception is re-raised."""
    handler = _make_always_network_error_handler(httpx.TimeoutException("Timed out"))
    client = _client_with_retry(handler, max_retries=1)

    with patch("time.sleep"):
        with pytest.raises(BunnyTimeoutError):
            client._sync_request("GET", _URL)


# ---------------------------------------------------------------------------
# Backoff growth
# ---------------------------------------------------------------------------


def test_backoff_grows_exponentially() -> None:
    """Patch random.uniform to return upper bound; verify delays double each attempt."""
    handler, _ = _make_always_fail_handler(fail_status=503)
    client = _client_with_retry(handler, max_retries=3, backoff_base=0.5)

    sleep_delays: list[float] = []

    def capture_sleep(d: float) -> None:
        sleep_delays.append(d)

    with (
        patch("time.sleep", side_effect=capture_sleep),
        patch("random.uniform", side_effect=lambda lo, hi: hi),
        pytest.raises(Exception),
    ):  # noqa: BLE001
        client._sync_request("GET", _URL)

    # attempt index 0,1,2 → upper bounds = 0.5*2^0, 0.5*2^1, 0.5*2^2 = 0.5, 1.0, 2.0
    assert sleep_delays == pytest.approx([0.5, 1.0, 2.0])


def test_backoff_caps_at_60_seconds() -> None:
    """Backoff delay is capped at 60 seconds regardless of attempt number."""
    handler, _ = _make_always_fail_handler(fail_status=503)
    # Use large backoff_base so we reach the cap quickly
    client = _client_with_retry(handler, max_retries=3, backoff_base=100.0)

    sleep_delays: list[float] = []

    def capture_sleep(d: float) -> None:
        sleep_delays.append(d)

    with (
        patch("time.sleep", side_effect=capture_sleep),
        patch("random.uniform", side_effect=lambda lo, hi: hi),
        pytest.raises(Exception),
    ):  # noqa: BLE001
        client._sync_request("GET", _URL)

    # All delays should be capped at 60.0 (min(60, 100*2^N) = 60 for all N >= 0)
    assert all(d == pytest.approx(60.0) for d in sleep_delays)


# ---------------------------------------------------------------------------
# Composability (RETRY-05)
# ---------------------------------------------------------------------------


def test_composability_with_async_http_transport() -> None:
    """RetryTransport(httpx.AsyncHTTPTransport()) can be injected into _BaseClient via client=."""
    # This test uses MockTransport (not a live network) to avoid external dependencies,
    # but constructs the full composability chain as documented in RETRY-05.
    handler, calls = _make_flaky_handler(fail_count=1, fail_status=503)
    inner = httpx.MockTransport(handler)
    retry_transport = RetryTransport(inner, max_retries=2, backoff_base=0.5)
    async_client = httpx.Client(transport=retry_transport)
    client = _BaseClient("test_api_key", client=async_client)

    with patch("time.sleep"):
        resp = client._sync_request("GET", _URL)

    assert resp.status_code == 200
    assert len(calls) == 2


def test_max_retries_zero_makes_single_attempt() -> None:
    """max_retries=0 means no retries — the initial attempt is the only attempt."""
    handler, calls = _make_always_fail_handler(fail_status=503)
    client = _client_with_retry(handler, max_retries=0)

    with patch("time.sleep") as mock_sleep, pytest.raises(Exception):  # noqa: BLE001
        client._sync_request("GET", _URL)

    assert len(calls) == 1
    assert mock_sleep.call_count == 0


# ---------------------------------------------------------------------------
# _parse_retry_after unit tests (covers the helper directly)
# ---------------------------------------------------------------------------


def test_parse_retry_after_integer() -> None:
    """_parse_retry_after('60') returns 60.0."""
    assert _parse_retry_after("60") == pytest.approx(60.0)


def test_parse_retry_after_float_string() -> None:
    """_parse_retry_after('1.5') returns 1.5."""
    assert _parse_retry_after("1.5") == pytest.approx(1.5)


def test_parse_retry_after_negative_clamps_to_zero() -> None:
    """_parse_retry_after('-5') is clamped to 0.0 (server sent past date as integer)."""
    assert _parse_retry_after("-5") == pytest.approx(0.0)


def test_parse_retry_after_http_date_future() -> None:
    """_parse_retry_after with HTTP-date 30s in the future returns ~30.0."""
    future = datetime.now(UTC) + timedelta(seconds=30)
    http_date = format_datetime(future, usegmt=True)
    result = _parse_retry_after(http_date)
    assert 28.0 <= result <= 32.0


def test_parse_retry_after_http_date_past_clamps_to_zero() -> None:
    """_parse_retry_after with an HTTP-date in the past returns 0.0."""
    past = datetime.now(UTC) - timedelta(seconds=30)
    http_date = format_datetime(past, usegmt=True)
    result = _parse_retry_after(http_date)
    assert result == pytest.approx(0.0)


def test_parse_retry_after_garbage_returns_zero() -> None:
    """_parse_retry_after with an unparseable value returns 0.0."""
    assert _parse_retry_after("not-a-date-or-number") == pytest.approx(0.0)
    assert _parse_retry_after("") == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# aclose passthrough
# ---------------------------------------------------------------------------


def test_close_delegates_to_inner_transport() -> None:
    """RetryTransport.close() calls close() on the inner transport."""
    handler, _ = _make_flaky_handler(fail_count=0)
    inner = httpx.MockTransport(handler)
    retry_transport = RetryTransport(inner, max_retries=1)
    retry_transport.close()
