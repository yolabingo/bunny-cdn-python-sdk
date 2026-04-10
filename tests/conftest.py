"""Shared test fixtures and helpers."""
from __future__ import annotations

from typing import Callable

import httpx

from bunny_cdn_sdk._client import _BaseClient
from bunny_cdn_sdk.storage import StorageClient


def make_base_client(handler: Callable[[httpx.Request], httpx.Response]) -> _BaseClient:
    """Create a _BaseClient with a MockTransport handler."""
    transport = httpx.MockTransport(handler)
    async_client = httpx.AsyncClient(transport=transport)
    return _BaseClient("test_api_key", client=async_client)


def make_storage_client(
    handler: Callable[[httpx.Request], httpx.Response],
    region: str = "falkenstein",
) -> StorageClient:
    """Create a StorageClient with a MockTransport handler."""
    transport = httpx.MockTransport(handler)
    async_client = httpx.AsyncClient(transport=transport)
    return StorageClient("my-zone", "test_password", region=region, client=async_client)
