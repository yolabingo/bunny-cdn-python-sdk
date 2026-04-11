"""Tests for top-level purge command (UTIL-01)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from bunny_cdn_sdk._exceptions import BunnyNotFoundError
from bunny_cdn_sdk.cli import app

TEST_URL = "https://cdn.example.com/image.jpg"


def _mock_exc(cls: type, status_code: int = 400, message: str = "err") -> object:
    return cls(status_code=status_code, message=message, response=MagicMock())


def test_purge_success(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.purge_url.return_value = {}
        result = runner.invoke(app, ["--api-key", "k", "purge", TEST_URL])
    assert result.exit_code == 0
    assert f"Purged: {TEST_URL}" in result.output


def test_purge_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.purge_url.side_effect = _mock_exc(BunnyNotFoundError, 404)
        result = runner.invoke(app, ["--api-key", "k", "purge", TEST_URL])
    assert result.exit_code == 1


def test_purge_missing_auth(runner) -> None:
    result = runner.invoke(app, ["purge", TEST_URL])
    assert result.exit_code == 1


def test_purge_called_with_correct_url(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.purge_url.return_value = {}
        runner.invoke(app, ["--api-key", "k", "purge", TEST_URL])
    mock_client.purge_url.assert_called_once_with(TEST_URL)
