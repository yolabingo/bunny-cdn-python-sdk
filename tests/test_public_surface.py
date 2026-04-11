"""Smoke test: verify the public bunny_cdn_sdk package surface resolves at import time."""

from __future__ import annotations


def test_public_imports() -> None:
    from bunny_cdn_sdk import BunnyAPIError, CoreClient, StorageClient

    assert CoreClient is not None
    assert StorageClient is not None
    assert BunnyAPIError is not None
