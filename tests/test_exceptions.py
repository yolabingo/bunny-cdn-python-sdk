"""Tests for exception hierarchy mapping in _client._request()."""
from __future__ import annotations

import httpx
import pytest

from bunny_cdn_sdk._exceptions import (
    BunnyAPIError,
    BunnyAuthenticationError,
    BunnyConnectionError,
    BunnyNotFoundError,
    BunnyRateLimitError,
    BunnyServerError,
    BunnyTimeoutError,
)
from tests.conftest import make_base_client

_URL = "https://api.bunnycdn.com/pullzone/1"


def _status_handler(status: int):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"Message": "error"})
    return handler


def test_authentication_error() -> None:
    client = make_base_client(_status_handler(401))
    with pytest.raises(BunnyAuthenticationError) as exc_info:
        client._sync_request("GET", _URL)
    assert exc_info.value.status_code == 401
    assert isinstance(exc_info.value, BunnyAPIError)


def test_not_found_error() -> None:
    client = make_base_client(_status_handler(404))
    with pytest.raises(BunnyNotFoundError) as exc_info:
        client._sync_request("GET", _URL)
    assert exc_info.value.status_code == 404


def test_rate_limit_error() -> None:
    client = make_base_client(_status_handler(429))
    with pytest.raises(BunnyRateLimitError) as exc_info:
        client._sync_request("GET", _URL)
    assert exc_info.value.status_code == 429


def test_server_error() -> None:
    client = make_base_client(_status_handler(500))
    with pytest.raises(BunnyServerError) as exc_info:
        client._sync_request("GET", _URL)
    assert exc_info.value.status_code == 500
    assert isinstance(exc_info.value, BunnyAPIError)


def test_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")
    client = make_base_client(handler)
    with pytest.raises(BunnyConnectionError) as exc_info:
        client._sync_request("GET", _URL)
    assert not isinstance(exc_info.value, BunnyAPIError)


def test_timeout_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Timed out")
    client = make_base_client(handler)
    with pytest.raises(BunnyTimeoutError) as exc_info:
        client._sync_request("GET", _URL)
    assert isinstance(exc_info.value, BunnyConnectionError)
