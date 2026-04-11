"""Tests for storage-zone CLI commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from bunny_cdn_sdk._exceptions import BunnyAPIError, BunnyAuthenticationError, BunnyNotFoundError
from bunny_cdn_sdk.cli import app

STORAGE_ZONE = {"Id": 2, "Name": "my-storage", "Region": "DE"}


def _mock_exc(cls: type, status_code: int = 400, message: str = "err") -> object:
    return cls(status_code=status_code, message=message, response=MagicMock())


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_storage_zone_list_success(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.iter_storage_zones.return_value = iter([STORAGE_ZONE])
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "list"])
    assert result.exit_code == 0
    assert "my-storage" in result.output


def test_storage_zone_list_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.iter_storage_zones.side_effect = _mock_exc(BunnyAuthenticationError, 401)
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "list"])
    assert result.exit_code == 1


def test_storage_zone_list_json(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.iter_storage_zones.return_value = iter([STORAGE_ZONE])
        result = runner.invoke(app, ["--api-key", "k", "--json", "storage-zone", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["Name"] == "my-storage"


def test_storage_zone_list_missing_auth(runner) -> None:
    result = runner.invoke(app, ["storage-zone", "list"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_storage_zone_get_success(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_storage_zone.return_value = STORAGE_ZONE
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "get", "2"])
    assert result.exit_code == 0
    assert "my-storage" in result.output


def test_storage_zone_get_not_found(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_storage_zone.side_effect = _mock_exc(BunnyNotFoundError, 404)
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "get", "999"])
    assert result.exit_code == 1


def test_storage_zone_get_json(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_storage_zone.return_value = STORAGE_ZONE
        result = runner.invoke(app, ["--api-key", "k", "--json", "storage-zone", "get", "2"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Id"] == 2


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_storage_zone_create_success(runner) -> None:
    created = {**STORAGE_ZONE, "Name": "new-storage"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.create_storage_zone.return_value = created
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "create", "--name", "new-storage"])
    assert result.exit_code == 0
    assert "new-storage" in result.output


def test_storage_zone_create_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.create_storage_zone.side_effect = _mock_exc(BunnyAPIError, 422)
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "create", "--name", "z"])
    assert result.exit_code == 1


def test_storage_zone_create_json(runner) -> None:
    created = {**STORAGE_ZONE, "Name": "new-storage"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.create_storage_zone.return_value = created
        result = runner.invoke(
            app, ["--api-key", "k", "--json", "storage-zone", "create", "--name", "new-storage"]
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Name"] == "new-storage"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_storage_zone_delete_with_yes(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_storage_zone.return_value = STORAGE_ZONE
        MockClient.return_value.delete_storage_zone.return_value = {}
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "delete", "2", "--yes"])
    assert result.exit_code == 0
    assert "Deleted storage zone 2" in result.output


def test_storage_zone_delete_prompt_confirmed(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_storage_zone.return_value = STORAGE_ZONE
        MockClient.return_value.delete_storage_zone.return_value = {}
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "delete", "2"], input="y\n")
    assert result.exit_code == 0


def test_storage_zone_delete_prompt_aborted(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_storage_zone.return_value = STORAGE_ZONE
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "delete", "2"], input="n\n")
    assert result.exit_code != 0


def test_storage_zone_delete_not_found(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_storage_zone.side_effect = _mock_exc(BunnyNotFoundError, 404)
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "delete", "999", "--yes"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_storage_zone_update_success_shows_diff(runner) -> None:
    before = {**STORAGE_ZONE, "Region": "DE"}
    after = {**STORAGE_ZONE, "Region": "UK"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_storage_zone.return_value = before
        MockClient.return_value.update_storage_zone.return_value = after
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "update", "2", "--set", "Region=UK"])
    assert result.exit_code == 0
    assert "Region" in result.output


def test_storage_zone_update_json(runner) -> None:
    after = {**STORAGE_ZONE, "Region": "UK"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_storage_zone.return_value = STORAGE_ZONE
        MockClient.return_value.update_storage_zone.return_value = after
        result = runner.invoke(
            app, ["--api-key", "k", "--json", "storage-zone", "update", "2", "--set", "Region=UK"]
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Region"] == "UK"


def test_storage_zone_update_malformed_set(runner) -> None:
    result = runner.invoke(app, ["--api-key", "k", "storage-zone", "update", "2", "--set", "NOEQUALS"])
    assert result.exit_code == 1


def test_storage_zone_update_error_on_get(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_storage_zone.side_effect = _mock_exc(BunnyNotFoundError, 404)
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "update", "2", "--set", "Name=x"])
    assert result.exit_code == 1


def test_storage_zone_update_no_fields_changed(runner) -> None:
    # Same before and after — should show "No fields changed"
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_storage_zone.return_value = STORAGE_ZONE
        MockClient.return_value.update_storage_zone.return_value = STORAGE_ZONE
        result = runner.invoke(app, ["--api-key", "k", "storage-zone", "update", "2", "--set", "Region=DE"])
    assert result.exit_code == 0
    assert "No fields changed" in result.output
