"""Shared test fixtures and helpers."""

from __future__ import annotations

from collections.abc import Callable

import httpx2

from bunny_cdn_sdk._client import _BaseClient
from bunny_cdn_sdk.storage import StorageClient


def make_base_client(handler: Callable[[httpx2.Request], httpx2.Response]) -> _BaseClient:
    """Create a _BaseClient with a MockTransport handler."""
    transport = httpx2.MockTransport(handler)
    async_client = httpx2.Client(transport=transport)
    return _BaseClient("test_api_key", client=async_client)


def make_storage_client(
    handler: Callable[[httpx2.Request], httpx2.Response],
    region: str = "falkenstein",
) -> StorageClient:
    """Create a StorageClient with a MockTransport handler."""
    transport = httpx2.MockTransport(handler)
    async_client = httpx2.Client(transport=transport)
    return StorageClient("my-zone", "test_password", region=region, client=async_client)
