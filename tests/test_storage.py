"""Tests for StorageClient operations and region mapping."""
from __future__ import annotations

import io

import httpx
import pytest

from bunny_cdn_sdk.storage import REGION_MAP, StorageClient
from tests.conftest import make_storage_client


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


def test_upload_bytes_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    client = make_storage_client(handler)
    result = client.upload("photos/image.jpg", b"hello")
    assert result == {}


def test_upload_binary_io_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    client = make_storage_client(handler)
    result = client.upload("photos/image.jpg", io.BytesIO(b"hello"))
    assert result == {}


def test_upload_with_content_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    client = make_storage_client(handler)
    result = client.upload("photos/image.jpg", b"data", content_type="image/jpeg")
    assert result == {}


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def test_download_returns_bytes() -> None:
    payload = b"file content bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload)

    client = make_storage_client(handler)
    result = client.download("photos/image.jpg")
    assert isinstance(result, bytes)
    assert result == payload


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    client = make_storage_client(handler)
    result = client.delete("photos/image.jpg")
    assert result is None


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def test_list_returns_list_of_dicts() -> None:
    files = [{"ObjectName": "img.jpg", "Length": 1024}]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=files)

    client = make_storage_client(handler)
    result = client.list("/")
    assert isinstance(result, list)
    assert result == files


# ---------------------------------------------------------------------------
# Region mapping
# ---------------------------------------------------------------------------


def test_region_falkenstein_base_url() -> None:
    client = StorageClient("zone", "password", region="falkenstein")
    assert client.base_url == REGION_MAP["falkenstein"]
    assert client.base_url == "https://storage.bunnycdn.com"


def test_region_ny_base_url() -> None:
    client = StorageClient("zone", "password", region="ny")
    assert client.base_url == REGION_MAP["ny"]
    assert client.base_url == "https://ny.storage.bunnycdn.com"


def test_invalid_region_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown region"):
        StorageClient("zone", "password", region="invalid-region")
