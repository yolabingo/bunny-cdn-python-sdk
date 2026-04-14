"""Tests for video-library CLI commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from bunny_cdn_sdk._exceptions import BunnyAPIError, BunnyAuthenticationError, BunnyNotFoundError
from bunny_cdn_sdk.cli import app

VIDEO_LIB = {"Id": 5, "Name": "my-videos", "VideoCount": 42}


def _mock_exc(cls: type, status_code: int = 400, message: str = "err") -> object:
    return cls(status_code=status_code, message=message, response=MagicMock())


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_video_library_list_success(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.iter_video_libraries.return_value = iter([VIDEO_LIB])
        result = runner.invoke(app, ["--api-key", "k", "video-library", "list"])
    assert result.exit_code == 0
    assert "my-videos" in result.output


def test_video_library_list_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.iter_video_libraries.side_effect = _mock_exc(BunnyAuthenticationError, 401)
        result = runner.invoke(app, ["--api-key", "k", "video-library", "list"])
    assert result.exit_code == 1


def test_video_library_list_json(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.iter_video_libraries.return_value = iter([VIDEO_LIB])
        result = runner.invoke(app, ["--api-key", "k", "--json", "video-library", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["Name"] == "my-videos"


def test_video_library_list_missing_auth(runner) -> None:
    result = runner.invoke(app, ["video-library", "list"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_video_library_get_success(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_video_library.return_value = VIDEO_LIB
        result = runner.invoke(app, ["--api-key", "k", "video-library", "get", "5"])
    assert result.exit_code == 0
    assert "my-videos" in result.output


def test_video_library_get_not_found(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_video_library.side_effect = _mock_exc(BunnyNotFoundError, 404)
        result = runner.invoke(app, ["--api-key", "k", "video-library", "get", "999"])
    assert result.exit_code == 1


def test_video_library_get_json(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_video_library.return_value = VIDEO_LIB
        result = runner.invoke(app, ["--api-key", "k", "--json", "video-library", "get", "5"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Id"] == 5


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_video_library_create_success(runner) -> None:
    created = {**VIDEO_LIB, "Name": "new-lib"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.create_video_library.return_value = created
        result = runner.invoke(
            app, ["--api-key", "k", "video-library", "create", "--name", "new-lib"]
        )
    assert result.exit_code == 0
    assert "new-lib" in result.output


def test_video_library_create_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.create_video_library.side_effect = _mock_exc(BunnyAPIError, 422)
        result = runner.invoke(app, ["--api-key", "k", "video-library", "create", "--name", "bad"])
    assert result.exit_code == 1


def test_video_library_create_json(runner) -> None:
    created = {**VIDEO_LIB, "Name": "new-lib"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.create_video_library.return_value = created
        result = runner.invoke(
            app, ["--api-key", "k", "--json", "video-library", "create", "--name", "new-lib"]
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Name"] == "new-lib"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_video_library_delete_with_yes(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_video_library.return_value = VIDEO_LIB
        MockClient.return_value.delete_video_library.return_value = {}
        result = runner.invoke(app, ["--api-key", "k", "video-library", "delete", "5", "--yes"])
    assert result.exit_code == 0
    assert "Deleted video library 5 (my-videos)." in result.output


def test_video_library_delete_prompt_aborted(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_video_library.return_value = VIDEO_LIB
        result = runner.invoke(app, ["--api-key", "k", "video-library", "delete", "5"], input="n\n")
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_video_library_update_success(runner) -> None:
    before = {**VIDEO_LIB, "Name": "old-name"}
    after = {**VIDEO_LIB, "Name": "new-name"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_video_library.return_value = before
        MockClient.return_value.update_video_library.return_value = after
        result = runner.invoke(
            app,
            ["--api-key", "k", "video-library", "update", "5", "--set", "Name=new-name"],
        )
    assert result.exit_code == 0


def test_video_library_update_json(runner) -> None:
    after = {**VIDEO_LIB, "Name": "new-name"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_video_library.return_value = VIDEO_LIB
        MockClient.return_value.update_video_library.return_value = after
        result = runner.invoke(
            app,
            ["--api-key", "k", "--json", "video-library", "update", "5", "--set", "Name=new-name"],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Name"] == "new-name"


def test_video_library_update_malformed_set(runner) -> None:
    result = runner.invoke(
        app, ["--api-key", "k", "video-library", "update", "5", "--set", "NOEQUALS"]
    )
    assert result.exit_code == 1
