"""Tests for dns-zone CLI commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from bunny_cdn_sdk._exceptions import BunnyAPIError, BunnyAuthenticationError, BunnyNotFoundError
from bunny_cdn_sdk.cli import app

DNS_ZONE = {"Id": 10, "Domain": "example.com", "RecordsCount": 3, "Records": []}
DNS_RECORD = {"Id": 99, "Name": "www", "Type": "A", "Value": "1.2.3.4"}


def _mock_exc(cls: type, status_code: int = 400, message: str = "err") -> object:
    return cls(status_code=status_code, message=message, response=MagicMock())


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_dns_zone_list_success(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.iter_dns_zones.return_value = iter([DNS_ZONE])
        result = runner.invoke(app, ["--api-key", "k", "dns-zone", "list"])
    assert result.exit_code == 0
    assert "example.com" in result.output


def test_dns_zone_list_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.iter_dns_zones.side_effect = _mock_exc(BunnyAuthenticationError, 401)
        result = runner.invoke(app, ["--api-key", "k", "dns-zone", "list"])
    assert result.exit_code == 1


def test_dns_zone_list_json(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.iter_dns_zones.return_value = iter([DNS_ZONE])
        result = runner.invoke(app, ["--api-key", "k", "--json", "dns-zone", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["Domain"] == "example.com"


def test_dns_zone_list_missing_auth(runner) -> None:
    result = runner.invoke(app, ["dns-zone", "list"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_dns_zone_get_success(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_dns_zone.return_value = DNS_ZONE
        result = runner.invoke(app, ["--api-key", "k", "dns-zone", "get", "10"])
    assert result.exit_code == 0
    assert "example.com" in result.output


def test_dns_zone_get_not_found(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_dns_zone.side_effect = _mock_exc(BunnyNotFoundError, 404)
        result = runner.invoke(app, ["--api-key", "k", "dns-zone", "get", "999"])
    assert result.exit_code == 1


def test_dns_zone_get_json(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_dns_zone.return_value = DNS_ZONE
        result = runner.invoke(app, ["--api-key", "k", "--json", "dns-zone", "get", "10"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Id"] == 10


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_dns_zone_create_success(runner) -> None:
    created = {**DNS_ZONE, "Domain": "newzone.com"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.create_dns_zone.return_value = created
        result = runner.invoke(app, ["--api-key", "k", "dns-zone", "create", "--domain", "newzone.com"])
    assert result.exit_code == 0
    assert "newzone.com" in result.output


def test_dns_zone_create_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.create_dns_zone.side_effect = _mock_exc(BunnyAPIError, 422)
        result = runner.invoke(app, ["--api-key", "k", "dns-zone", "create", "--domain", "bad.com"])
    assert result.exit_code == 1


def test_dns_zone_create_json(runner) -> None:
    created = {**DNS_ZONE, "Domain": "newzone.com"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.create_dns_zone.return_value = created
        result = runner.invoke(
            app, ["--api-key", "k", "--json", "dns-zone", "create", "--domain", "newzone.com"]
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Domain"] == "newzone.com"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_dns_zone_delete_with_yes(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_dns_zone.return_value = DNS_ZONE
        MockClient.return_value.delete_dns_zone.return_value = {}
        result = runner.invoke(app, ["--api-key", "k", "dns-zone", "delete", "10", "--yes"])
    assert result.exit_code == 0
    assert "Deleted DNS zone 10" in result.output


def test_dns_zone_delete_prompt_aborted(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_dns_zone.return_value = DNS_ZONE
        result = runner.invoke(app, ["--api-key", "k", "dns-zone", "delete", "10"], input="n\n")
    assert result.exit_code != 0


def test_dns_zone_delete_not_found(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_dns_zone.side_effect = _mock_exc(BunnyNotFoundError, 404)
        result = runner.invoke(app, ["--api-key", "k", "dns-zone", "delete", "999", "--yes"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# record add
# ---------------------------------------------------------------------------


def test_dns_zone_record_add_success(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.add_dns_record.return_value = DNS_RECORD
        result = runner.invoke(
            app,
            [
                "--api-key", "k",
                "dns-zone", "record", "add", "10",
                "--type", "A",
                "--name", "www",
                "--value", "1.2.3.4",
            ],
        )
    assert result.exit_code == 0
    assert "www" in result.output


def test_dns_zone_record_add_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.add_dns_record.side_effect = _mock_exc(BunnyAPIError, 422)
        result = runner.invoke(
            app,
            [
                "--api-key", "k",
                "dns-zone", "record", "add", "10",
                "--type", "A",
                "--name", "www",
                "--value", "1.2.3.4",
            ],
        )
    assert result.exit_code == 1


def test_dns_zone_record_add_json(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.add_dns_record.return_value = DNS_RECORD
        result = runner.invoke(
            app,
            [
                "--api-key", "k",
                "--json",
                "dns-zone", "record", "add", "10",
                "--type", "A",
                "--name", "www",
                "--value", "1.2.3.4",
            ],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Name"] == "www"


# ---------------------------------------------------------------------------
# record update
# ---------------------------------------------------------------------------


def test_dns_zone_record_update_success(runner) -> None:
    zone_with_record = {**DNS_ZONE, "Records": [DNS_RECORD]}
    updated_record = {**DNS_RECORD, "Value": "5.6.7.8"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_dns_zone.return_value = zone_with_record
        MockClient.return_value.update_dns_record.return_value = updated_record
        result = runner.invoke(
            app,
            [
                "--api-key", "k",
                "dns-zone", "record", "update", "10", "99",
                "--set", "Value=5.6.7.8",
            ],
        )
    assert result.exit_code == 0


def test_dns_zone_record_update_json(runner) -> None:
    zone_with_record = {**DNS_ZONE, "Records": [DNS_RECORD]}
    updated_record = {**DNS_RECORD, "Value": "5.6.7.8"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_dns_zone.return_value = zone_with_record
        MockClient.return_value.update_dns_record.return_value = updated_record
        result = runner.invoke(
            app,
            [
                "--api-key", "k",
                "--json",
                "dns-zone", "record", "update", "10", "99",
                "--set", "Value=5.6.7.8",
            ],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Value"] == "5.6.7.8"


def test_dns_zone_record_update_malformed_set(runner) -> None:
    result = runner.invoke(
        app,
        ["--api-key", "k", "dns-zone", "record", "update", "10", "99", "--set", "NOEQUALS"],
    )
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# record delete
# ---------------------------------------------------------------------------


def test_dns_zone_record_delete_with_yes(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.delete_dns_record.return_value = {}
        result = runner.invoke(
            app,
            ["--api-key", "k", "dns-zone", "record", "delete", "10", "99", "--yes"],
        )
    assert result.exit_code == 0
    assert "Deleted DNS record 99" in result.output


def test_dns_zone_record_delete_prompt_aborted(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient"):
        result = runner.invoke(
            app,
            ["--api-key", "k", "dns-zone", "record", "delete", "10", "99"],
            input="n\n",
        )
    assert result.exit_code != 0
