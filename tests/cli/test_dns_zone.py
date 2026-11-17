"""Tests for dns-zone CLI commands."""

from __future__ import annotations

import json
import re
from unittest.mock import MagicMock, patch

import pytest

from bunny_cdn_sdk._exceptions import BunnyAPIError, BunnyAuthenticationError, BunnyNotFoundError
from bunny_cdn_sdk.cli import app

DNS_ZONE = {"Id": 10, "Domain": "example.com", "RecordsCount": 3, "Records": []}
DNS_RECORD = {"Id": 99, "Name": "www", "Type": 0, "Value": "1.2.3.4"}


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
        result = runner.invoke(
            app, ["--api-key", "k", "--output-format", "json", "dns-zone", "list"]
        )
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
        result = runner.invoke(
            app, ["--api-key", "k", "--output-format", "json", "dns-zone", "get", "10"]
        )
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
        result = runner.invoke(
            app, ["--api-key", "k", "dns-zone", "create", "--domain", "newzone.com"]
        )
    assert result.exit_code == 0
    assert "newzone.com" in result.output
    MockClient.return_value.create_dns_zone.assert_called_once_with(Domain="newzone.com")


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
            app,
            [
                "--api-key",
                "k",
                "--output-format",
                "json",
                "dns-zone",
                "create",
                "--domain",
                "newzone.com",
            ],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Domain"] == "newzone.com"
    MockClient.return_value.create_dns_zone.assert_called_once_with(Domain="newzone.com")


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
    MockClient.return_value.delete_dns_zone.assert_called_once_with(10)


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
                "--api-key",
                "k",
                "dns-zone",
                "record",
                "add",
                "10",
                "--type",
                "A",
                "--name",
                "www",
                "--value",
                "1.2.3.4",
            ],
        )
    assert result.exit_code == 0
    assert "www" in result.output
    MockClient.return_value.add_dns_record.assert_called_once_with(
        10, Type=0, Name="www", Value="1.2.3.4", Ttl=300
    )


def test_dns_zone_record_add_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.add_dns_record.side_effect = _mock_exc(BunnyAPIError, 422)
        result = runner.invoke(
            app,
            [
                "--api-key",
                "k",
                "dns-zone",
                "record",
                "add",
                "10",
                "--type",
                "A",
                "--name",
                "www",
                "--value",
                "1.2.3.4",
            ],
        )
    assert result.exit_code == 1


def test_dns_zone_record_add_json(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.add_dns_record.return_value = DNS_RECORD
        result = runner.invoke(
            app,
            [
                "--api-key",
                "k",
                "--output-format",
                "json",
                "dns-zone",
                "record",
                "add",
                "10",
                "--type",
                "A",
                "--name",
                "www",
                "--value",
                "1.2.3.4",
            ],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Name"] == "www"
    MockClient.return_value.add_dns_record.assert_called_once_with(
        10, Type=0, Name="www", Value="1.2.3.4", Ttl=300
    )


def _add(runner, *args: str, fmt: tuple[str, ...] = ()):
    return runner.invoke(
        app, ["--api-key", "k", *fmt, "dns-zone", "record", "add", "10", "--name", "@", *args]
    )


def test_dns_zone_record_add_mx_priority(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.add_dns_record.return_value = DNS_RECORD
        result = _add(runner, "--type", "MX", "--value", "mail.example.com", "--priority", "10")
    assert result.exit_code == 0
    MockClient.return_value.add_dns_record.assert_called_once_with(
        10, Type=4, Name="@", Value="mail.example.com", Ttl=300, Priority=10
    )


def test_dns_zone_record_add_srv_all_fields(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.add_dns_record.return_value = DNS_RECORD
        result = _add(
            runner, "--type", "srv", "--value", "sip.example.com",
            "--priority", "0", "--weight", "5", "--port", "5060",
        )  # fmt: skip
    assert result.exit_code == 0
    MockClient.return_value.add_dns_record.assert_called_once_with(
        10, Type=8, Name="@", Value="sip.example.com", Ttl=300, Priority=0, Weight=5, Port=5060
    )


@pytest.mark.parametrize(
    ("args", "missing"),
    [
        (["--type", "MX"], "--priority"),
        (["--type", "SRV", "--weight", "1", "--port", "2"], "--priority"),
        (["--type", "SRV", "--priority", "1", "--port", "2"], "--weight"),
        (["--type", "SRV", "--priority", "1", "--weight", "2"], "--port"),
    ],
)
def test_dns_zone_record_add_requires_fields(runner, args, missing) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        result = _add(runner, *args, "--value", "x.example.com")
    assert result.exit_code == 2
    assert f"Invalid value for {missing}" in re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    MockClient.return_value.add_dns_record.assert_not_called()


@pytest.mark.parametrize("flag", ["--priority", "--weight", "--port"])
def test_dns_zone_record_add_rejects_srv_fields_on_a(runner, flag) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        result = _add(runner, "--type", "A", "--value", "1.2.3.4", flag, "1")
    assert result.exit_code == 2
    assert "does not apply to A" in re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    MockClient.return_value.add_dns_record.assert_not_called()


def test_dns_zone_record_add_rejects_weight_on_mx(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient"):
        result = _add(
            runner, "--type", "MX", "--value", "m.example.com", "--priority", "1", "--weight", "1"
        )
    assert result.exit_code == 2


def test_dns_zone_record_add_negative_priority(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient"):
        result = _add(runner, "--type", "MX", "--value", "m.example.com", "--priority", "-1")
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# record list
# ---------------------------------------------------------------------------

RECORDS = [
    {"Id": 3, "Name": "www", "Type": 2, "Value": "a.example.com", "Ttl": 300, "Priority": None},
    {"Id": 1, "Name": "", "Type": 4, "Value": "mail.example.com", "Ttl": 600, "Priority": 10},
    {"Id": 2, "Name": "www", "Type": 0, "Value": "1.2.3.4", "Ttl": 300, "Priority": 0},
    {"Id": 4, "Name": "api", "Type": 0, "Value": "5.6.7.8", "Ttl": 300, "Priority": 0},
    {"Id": 5, "Name": "odd", "Type": 99, "Value": "?", "Ttl": 300, "Priority": 0},
]


def _list(runner, records, *fmt: str):
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_dns_zone.return_value = {**DNS_ZONE, "Records": records}
        result = runner.invoke(app, ["--api-key", "k", *fmt, "dns-zone", "record", "list", "10"])
    MockClient.return_value.get_dns_zone.assert_called_once_with(10)
    return result


def test_dns_zone_record_list_table(runner) -> None:
    result = _list(runner, RECORDS)
    assert result.exit_code == 0
    out = result.output
    for header in ("Id", "Name", "Type", "Value", "Ttl", "Priority"):
        assert header in out
    # Sorted by type name then name: 99, A api, A www, CNAME, MX (str sort: "99" first)
    order = [out.index(v) for v in ("odd", "api", "mail.example.com")]
    assert order == sorted(order)
    assert out.index("api") < out.index("1.2.3.4") < out.index("a.example.com")
    assert "@" in out  # empty Name is the zone root
    assert "MX" in out
    assert "CNAME" in out
    assert "99" in out  # out-of-range type shown raw


def test_dns_zone_record_list_sorts_name_within_type(runner) -> None:
    out = _list(runner, RECORDS).output
    assert out.index("5.6.7.8") < out.index("1.2.3.4")  # api before www, both A


def test_dns_zone_record_list_none_records(runner) -> None:
    result = _list(runner, None)
    assert result.exit_code == 0
    assert "Priority" in result.output


def test_dns_zone_record_list_json(runner) -> None:
    result = _list(runner, RECORDS, "--output-format", "json")
    assert result.exit_code == 0
    assert json.loads(result.output) == RECORDS


def test_dns_zone_record_list_error(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_dns_zone.side_effect = _mock_exc(BunnyNotFoundError, 404)
        result = runner.invoke(app, ["--api-key", "k", "dns-zone", "record", "list", "10"])
    assert result.exit_code == 1


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
                "--api-key",
                "k",
                "dns-zone",
                "record",
                "update",
                "10",
                "99",
                "--set",
                "Value=5.6.7.8",
            ],
        )
    assert result.exit_code == 0
    MockClient.return_value.update_dns_record.assert_called_once_with(10, 99, Value="5.6.7.8")


def test_dns_zone_record_update_json(runner) -> None:
    zone_with_record = {**DNS_ZONE, "Records": [DNS_RECORD]}
    updated_record = {**DNS_RECORD, "Value": "5.6.7.8"}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_dns_zone.return_value = zone_with_record
        MockClient.return_value.update_dns_record.return_value = updated_record
        result = runner.invoke(
            app,
            [
                "--api-key",
                "k",
                "--output-format",
                "json",
                "dns-zone",
                "record",
                "update",
                "10",
                "99",
                "--set",
                "Value=5.6.7.8",
            ],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["Value"] == "5.6.7.8"
    MockClient.return_value.update_dns_record.assert_called_once_with(10, 99, Value="5.6.7.8")


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
    MockClient.return_value.delete_dns_record.assert_called_once_with(10, 99)


def test_dns_zone_record_delete_prompt_aborted(runner) -> None:
    with patch("bunny_cdn_sdk.core.CoreClient"):
        result = runner.invoke(
            app,
            ["--api-key", "k", "dns-zone", "record", "delete", "10", "99"],
            input="n\n",
        )
    assert result.exit_code != 0


def test_record_add_maps_type_name_and_rejects_unknown(runner) -> None:
    with patch("bunny_cdn_sdk.cli._dns_zone.core.CoreClient") as MockClient:
        MockClient.return_value.add_dns_record.return_value = DNS_RECORD
        base = ["--api-key", "k", "dns-zone", "record", "add", "10", "--name", "w", "--value", "v"]
        ok = runner.invoke(app, [*base, "--type", "cname"])
        bad = runner.invoke(app, [*base, "--type", "BOGUS"])
    assert ok.exit_code == 0
    assert MockClient.return_value.add_dns_record.call_args.kwargs["Type"] == 2
    assert bad.exit_code != 0
    assert "unknown record type" in bad.output


_ADD = ["--api-key", "k", "dns-zone", "record", "add", "10", "--name", "w"]


@pytest.mark.parametrize(
    ("type_", "value", "sent"),
    [
        ("A", " 1.2.3.4", "1.2.3.4"),
        ("AAAA", "2001:DB8:0:0::1", "2001:db8::1"),  # normalized
        ("CNAME", "not-an-ip.example.com", "not-an-ip.example.com"),  # not checked
    ],
)
def test_record_add_accepts_valid_values(runner, type_, value, sent) -> None:
    with patch("bunny_cdn_sdk.cli._dns_zone.core.CoreClient") as MockClient:
        MockClient.return_value.add_dns_record.return_value = DNS_RECORD
        result = runner.invoke(app, [*_ADD, "--type", type_, "--value", value])
    assert result.exit_code == 0, result.output
    assert MockClient.return_value.add_dns_record.call_args.kwargs["Value"] == sent


@pytest.mark.parametrize(
    ("type_", "value"),
    [("A", "999.1.1.1"), ("A", "2001:db8::1"), ("AAAA", "1.2.3.4"), ("A", "example.com")],
)
def test_record_add_rejects_bad_ips(runner, type_, value) -> None:
    with patch("bunny_cdn_sdk.cli._dns_zone.core.CoreClient") as MockClient:
        result = runner.invoke(app, [*_ADD, "--type", type_, "--value", value])
    assert result.exit_code != 0
    assert "must be an IPv" in result.output
    MockClient.return_value.add_dns_record.assert_not_called()


def _update(runner, *sets: str):
    zone = {**DNS_ZONE, "Records": [DNS_RECORD]}  # an A record
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        MockClient.return_value.get_dns_zone.return_value = zone
        MockClient.return_value.update_dns_record.return_value = DNS_RECORD
        args = [a for s in sets for a in ("--set", s)]
        result = runner.invoke(
            app, ["--api-key", "k", "dns-zone", "record", "update", "10", "99", *args]
        )
    return result, MockClient.return_value.update_dns_record


def test_record_update_validates_value_against_existing_type(runner) -> None:
    result, update = _update(runner, "Value=not-an-ip")
    assert result.exit_code != 0
    assert "A record value must be an IPv4 address" in result.output
    update.assert_not_called()


def test_record_update_type_change_checks_existing_value(runner) -> None:
    result, update = _update(runner, "Type=AAAA")  # existing value is IPv4
    assert result.exit_code != 0
    update.assert_not_called()


def test_record_update_maps_type_name_and_skips_unrelated_fields(runner) -> None:
    result, update = _update(runner, "Type=CNAME", "Value=cdn.example.com")
    assert result.exit_code == 0, result.output
    update.assert_called_once_with(10, 99, Type=2, Value="cdn.example.com")
    result, update = _update(runner, "Ttl=60")
    assert result.exit_code == 0, result.output
    update.assert_called_once_with(10, 99, Ttl=60)
