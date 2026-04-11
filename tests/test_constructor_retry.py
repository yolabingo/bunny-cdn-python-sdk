"""Integration tests for constructor-level max_retries / backoff_base wiring.

These tests exercise the full path: CoreClient/StorageClient constructor
→ _BaseClient.__init__ → RetryTransport auto-wiring → actual retry behavior.

Pattern: create a CoreClient or StorageClient with max_retries=N, make a request
against a MockTransport that returns 500 repeatedly, and assert the correct call count.
time.sleep is patched to avoid real delays.
"""

from __future__ import annotations

import warnings
from unittest.mock import patch

import httpx
import pytest

from bunny_cdn_sdk import CoreClient, StorageClient
from bunny_cdn_sdk._exceptions import BunnyServerError
from bunny_cdn_sdk._retry import RetryTransport

_CORE_URL = "https://api.bunnycdn.com/pullzone/1"
_STORAGE_URL = "https://storage.bunnycdn.com/my-zone/file.txt"


# ---------------------------------------------------------------------------
# Local helpers (not in conftest to keep constructor tests self-contained)
# ---------------------------------------------------------------------------


def _always_500_handler():
    """Return (handler, call_list) — every call returns HTTP 500."""
    calls: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        return httpx.Response(500)

    return handler, calls


def _fail_then_succeed_handler(fail_count: int, fail_status: int = 500):
    """Return (handler, call_list) — fails fail_count times then returns 200."""
    calls: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        if len(calls) <= fail_count:
            return httpx.Response(fail_status)
        return httpx.Response(200, json={"ok": True})

    return handler, calls


# ---------------------------------------------------------------------------
# Backward compatibility — max_retries=0 default (v1.0 parity)
# ---------------------------------------------------------------------------


def test_core_client_default_no_retry_single_call() -> None:
    """CoreClient(api_key) with 500 response raises BunnyServerError after 1 attempt.

    max_retries=0 (default) must produce exactly 1 HTTP call — v1.0 parity.
    """
    handler, calls = _always_500_handler()
    transport = httpx.MockTransport(handler)
    client = CoreClient("test_api_key", client=httpx.Client(transport=transport))

    with patch("time.sleep") as mock_sleep, pytest.raises(BunnyServerError):
        client._sync_request("GET", _CORE_URL)

    assert len(calls) == 1, f"Expected 1 call, got {len(calls)}"
    assert mock_sleep.call_count == 0, "No sleep for max_retries=0"


def test_core_client_no_retry_transport_when_max_retries_zero() -> None:
    """CoreClient(api_key) with max_retries=0 does NOT wrap a Client in RetryTransport."""
    client = CoreClient("test_api_key")
    assert not isinstance(client._client._transport, RetryTransport), (
        "RetryTransport should not be present when max_retries=0"
    )


# ---------------------------------------------------------------------------
# CoreClient constructor auto-wiring
# ---------------------------------------------------------------------------


def test_core_client_max_retries_wires_retry_transport() -> None:
    """CoreClient(api_key, max_retries=N) auto-creates a RetryTransport-backed Client."""
    client = CoreClient("test_api_key", max_retries=3)
    assert isinstance(client._client._transport, RetryTransport), (
        "Expected RetryTransport to be auto-wired"
    )


def test_core_client_max_retries_2_produces_3_calls() -> None:
    """CoreClient with max_retries=2 and always-500 transport makes 3 total calls.

    1 initial + 2 retries = 3 total.
    """
    handler, calls = _always_500_handler()
    transport = httpx.MockTransport(handler)
    retry_transport = RetryTransport(transport, max_retries=2, backoff_base=0.0)
    client = CoreClient("test_api_key", client=httpx.Client(transport=retry_transport))

    with patch("time.sleep"), pytest.raises(BunnyServerError):
        client._sync_request("GET", _CORE_URL)

    assert len(calls) == 3, f"Expected 3 calls (1 + 2 retries), got {len(calls)}"


def test_core_client_constructor_max_retries_2_produces_3_calls() -> None:
    """CoreClient(api_key, max_retries=2) auto-wires RetryTransport; always-500 → 3 calls."""
    client = CoreClient("test_api_key", max_retries=2, backoff_base=0.0)
    assert isinstance(client._client._transport, RetryTransport)

    handler, calls = _always_500_handler()
    client._client._transport._inner = httpx.MockTransport(handler)

    with patch("time.sleep"), pytest.raises(BunnyServerError):
        client._sync_request("GET", _CORE_URL)

    assert len(calls) == 3, f"Expected 3 calls (1 + 2 retries), got {len(calls)}"


def test_core_client_max_retries_1_succeeds_on_second_call() -> None:
    """CoreClient(max_retries=1) with 1-fail handler succeeds on retry."""
    handler, calls = _fail_then_succeed_handler(fail_count=1)
    client = CoreClient("test_api_key", max_retries=1, backoff_base=0.0)
    client._client._transport._inner = httpx.MockTransport(handler)

    with patch("time.sleep"):
        resp = client._sync_request("GET", _CORE_URL)

    assert resp.status_code == 200
    assert len(calls) == 2, f"Expected 2 calls (1 fail + 1 success), got {len(calls)}"


# ---------------------------------------------------------------------------
# StorageClient constructor auto-wiring
# ---------------------------------------------------------------------------


def test_storage_client_max_retries_wires_retry_transport() -> None:
    """StorageClient(zone, pwd, max_retries=N) auto-creates a RetryTransport-backed Client."""
    client = StorageClient("my-zone", "test_password", max_retries=2)
    assert isinstance(client._client._transport, RetryTransport), (
        "Expected RetryTransport to be auto-wired"
    )


def test_storage_client_default_no_retry_single_call() -> None:
    """StorageClient(zone, pwd) with 500 response raises BunnyServerError after 1 attempt."""
    handler, calls = _always_500_handler()
    transport = httpx.MockTransport(handler)
    client = StorageClient("my-zone", "test_password", client=httpx.Client(transport=transport))

    with patch("time.sleep") as mock_sleep, pytest.raises(BunnyServerError):
        client._sync_request("GET", _STORAGE_URL)

    assert len(calls) == 1, f"Expected 1 call, got {len(calls)}"
    assert mock_sleep.call_count == 0


def test_storage_client_max_retries_1_produces_2_calls() -> None:
    """StorageClient(zone, pwd, max_retries=1) makes 2 total calls on always-500 transport."""
    client = StorageClient("my-zone", "test_password", max_retries=1, backoff_base=0.0)

    handler, calls = _always_500_handler()
    client._client._transport._inner = httpx.MockTransport(handler)

    with patch("time.sleep"), pytest.raises(BunnyServerError):
        client._sync_request("GET", _STORAGE_URL)

    assert len(calls) == 2, f"Expected 2 calls (1 + 1 retry), got {len(calls)}"


def test_storage_client_region_kwarg_still_works_with_max_retries() -> None:
    """StorageClient with region= and max_retries= together resolves correctly."""
    client = StorageClient("my-zone", "test_password", region="ny", max_retries=1)
    assert client.base_url == "https://ny.storage.bunnycdn.com"
    assert isinstance(client._client._transport, RetryTransport)


# ---------------------------------------------------------------------------
# backoff_base pass-through
# ---------------------------------------------------------------------------


def test_backoff_base_zero_skips_delay_but_still_retries() -> None:
    """backoff_base=0.0 means zero sleep delay, but retries still happen."""
    client = CoreClient("test_api_key", max_retries=2, backoff_base=0.0)
    handler, calls = _always_500_handler()
    client._client._transport._inner = httpx.MockTransport(handler)

    sleep_delays: list[float] = []

    def capture_sleep(d: float) -> None:
        sleep_delays.append(d)

    with patch("time.sleep", side_effect=capture_sleep), pytest.raises(BunnyServerError):
        client._sync_request("GET", _CORE_URL)

    assert len(calls) == 3
    assert len(sleep_delays) == 2
    assert all(d == pytest.approx(0.0) for d in sleep_delays)


# ---------------------------------------------------------------------------
# UserWarning on client= + max_retries conflict
# ---------------------------------------------------------------------------


def test_user_warning_when_client_and_max_retries_provided() -> None:
    """Providing client= and max_retries>0 emits exactly one UserWarning."""
    mock_client = httpx.Client()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client = CoreClient("test_api_key", client=mock_client, max_retries=2)

    assert len(caught) == 1, f"Expected 1 warning, got {len(caught)}: {caught}"
    assert issubclass(caught[0].category, UserWarning)
    assert "max_retries is ignored" in str(caught[0].message)
    assert "client= is provided" in str(caught[0].message)

    assert client._client is mock_client
    assert client._client_owner is False


def test_no_warning_when_only_client_provided() -> None:
    """Providing client= without max_retries does NOT emit a warning."""
    mock_client = httpx.Client()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        CoreClient("test_api_key", client=mock_client)

    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 0, f"Unexpected UserWarning: {user_warnings}"


def test_no_warning_when_max_retries_zero_and_client_provided() -> None:
    """client= + max_retries=0 (default) does NOT trigger the warning."""
    mock_client = httpx.Client()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        CoreClient("test_api_key", client=mock_client, max_retries=0)

    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 0


def test_user_warning_for_storage_client_client_plus_max_retries() -> None:
    """StorageClient also emits UserWarning when client= and max_retries>0 conflict."""
    mock_client = httpx.Client()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        StorageClient("my-zone", "pwd", client=mock_client, max_retries=1)

    assert len(caught) == 1
    assert issubclass(caught[0].category, UserWarning)
    assert "max_retries is ignored" in str(caught[0].message)
