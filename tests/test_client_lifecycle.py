"""Tests for _BaseClient context manager lifecycle (sync, _client_owner=True)."""

from __future__ import annotations

from bunny_cdn_sdk._client import _BaseClient


def test_sync_context_manager_lifecycle() -> None:
    """Sync context manager: __enter__ and __exit__ with _client_owner=True."""
    with _BaseClient("test-key") as client:
        assert client._client_owner is True
