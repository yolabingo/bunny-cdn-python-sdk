"""Tests for storage CLI commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from bunny_cdn_sdk._exceptions import BunnyAPIError, BunnyAuthenticationError
from bunny_cdn_sdk.cli import app

FILE_DICT = {
    "ObjectName": "image.jpg",
    "Length": 12345,
    "IsDirectory": False,
    "LastChanged": "2024-01-15T10:00:00",
}

_AUTH = ["--zone-name", "z", "--storage-key", "k"]  # reusable auth args


def _mock_exc(cls: type, status_code: int = 400, message: str = "err") -> object:
    return cls(status_code=status_code, message=message, response=MagicMock())


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_storage_list_success(runner) -> None:
    with patch("bunny_cdn_sdk.storage.StorageClient") as MockClient:
        MockClient.return_value.list.return_value = [FILE_DICT]
        result = runner.invoke(app, [*_AUTH, "storage", "list"])
    assert result.exit_code == 0
    assert "image.jpg" in result.output


def test_storage_list_error(runner) -> None:
    with patch("bunny_cdn_sdk.storage.StorageClient") as MockClient:
        MockClient.return_value.list.side_effect = _mock_exc(BunnyAuthenticationError, 401)
        result = runner.invoke(app, [*_AUTH, "storage", "list"])
    assert result.exit_code == 1


def test_storage_list_json(runner) -> None:
    with patch("bunny_cdn_sdk.storage.StorageClient") as MockClient:
        MockClient.return_value.list.return_value = [FILE_DICT]
        result = runner.invoke(app, [*_AUTH, "--json", "storage", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["ObjectName"] == "image.jpg"


def test_storage_list_missing_auth(runner) -> None:
    result = runner.invoke(app, ["storage", "list"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------


def test_storage_upload_success(runner, tmp_path) -> None:
    src = tmp_path / "file.txt"
    src.write_bytes(b"hello")
    with patch("bunny_cdn_sdk.storage.StorageClient") as MockClient:
        MockClient.return_value.upload.return_value = {}
        result = runner.invoke(app, [*_AUTH, "storage", "upload", str(src), "remote/file.txt"])
    assert result.exit_code == 0
    assert "Uploaded" in result.output


def test_storage_upload_file_not_found(runner, tmp_path) -> None:
    missing = str(tmp_path / "missing.txt")
    result = runner.invoke(app, [*_AUTH, "storage", "upload", missing, "remote/file.txt"])
    assert result.exit_code == 1


def test_storage_upload_error(runner, tmp_path) -> None:
    src = tmp_path / "file.txt"
    src.write_bytes(b"data")
    with patch("bunny_cdn_sdk.storage.StorageClient") as MockClient:
        MockClient.return_value.upload.side_effect = _mock_exc(BunnyAPIError, 422)
        result = runner.invoke(app, [*_AUTH, "storage", "upload", str(src), "remote/file.txt"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------


def test_storage_download_success(runner, tmp_path) -> None:
    dest = tmp_path / "out.txt"
    with patch("bunny_cdn_sdk.storage.StorageClient") as MockClient:
        MockClient.return_value.download.return_value = b"hello world"
        result = runner.invoke(app, [*_AUTH, "storage", "download", "remote/file.txt", str(dest)])
    assert result.exit_code == 0
    assert dest.read_bytes() == b"hello world"


def test_storage_download_error(runner, tmp_path) -> None:
    dest = tmp_path / "out.txt"
    with patch("bunny_cdn_sdk.storage.StorageClient") as MockClient:
        MockClient.return_value.download.side_effect = _mock_exc(BunnyAuthenticationError, 401)
        result = runner.invoke(app, [*_AUTH, "storage", "download", "remote/file.txt", str(dest)])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_storage_delete_with_yes(runner) -> None:
    with patch("bunny_cdn_sdk.storage.StorageClient") as MockClient:
        MockClient.return_value.delete.return_value = None
        result = runner.invoke(app, [*_AUTH, "storage", "delete", "remote/file.txt", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_storage_delete_prompt_confirmed(runner) -> None:
    with patch("bunny_cdn_sdk.storage.StorageClient") as MockClient:
        MockClient.return_value.delete.return_value = None
        result = runner.invoke(app, [*_AUTH, "storage", "delete", "remote/file.txt"], input="y\n")
    assert result.exit_code == 0


def test_storage_delete_prompt_aborted(runner) -> None:
    with patch("bunny_cdn_sdk.storage.StorageClient"):
        result = runner.invoke(app, [*_AUTH, "storage", "delete", "remote/file.txt"], input="n\n")
    assert result.exit_code != 0


def test_storage_delete_error(runner) -> None:
    with patch("bunny_cdn_sdk.storage.StorageClient") as MockClient:
        MockClient.return_value.delete.side_effect = _mock_exc(BunnyAPIError, 404)
        result = runner.invoke(app, [*_AUTH, "storage", "delete", "remote/file.txt", "--yes"])
    assert result.exit_code == 1
