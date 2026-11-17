"""Pull zone smoke tests: one live zone, exercised in file order, then deleted."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from bunny_cdn_sdk._exceptions import BunnyNotFoundError
from bunny_cdn_sdk.cli import app

from .conftest import DOMAIN_VAR, ORIGIN

if TYPE_CHECKING:
    from bunny_cdn_sdk import CoreClient, LoggingClient
    from bunny_cdn_sdk.models.core import EdgeRuleV2Model, PullZoneModel

SET_RESPONSE_HEADER = 5  # EdgeRuleActionType
TRIGGER_URL = 0  # TriggerTypes
MATCH_ANY = 0  # TriggerMatchingTypes / PatternMatchingTypes


def _rule(core: CoreClient, zone_id: int, description: str) -> EdgeRuleV2Model | None:
    rules = core.get_pull_zone(zone_id).get("EdgeRules") or []
    return next((r for r in rules if r.get("Description") == description), None)


def test_create_and_list(core: CoreClient, zone: PullZoneModel, zone_name: str) -> None:
    assert zone["Name"] == zone_name
    assert (zone.get("OriginUrl") or "").rstrip("/") == ORIGIN
    assert zone["Id"] in [z["Id"] for z in core.list_pull_zones()]


def test_search_finds_new_zone(core: CoreClient, zone: PullZoneModel, zone_name: str) -> None:
    # Search can lag behind creation, so poll briefly before failing.
    deadline = time.monotonic() + 30
    while zone["Id"] not in (ids := [z["Id"] for z in core.list_pull_zones(search=zone_name)]):
        if time.monotonic() > deadline:
            pytest.fail(f"search={zone_name!r} still missing the zone after 30s; got {ids}")
        time.sleep(3)


def test_update_settings(core: CoreClient, zone: PullZoneModel) -> None:
    core.update_pull_zone(zone["Id"], CacheControlMaxAgeOverride=3600, EnableLogging=True)
    got = core.get_pull_zone(zone["Id"])
    assert got["CacheControlMaxAgeOverride"] == 3600
    assert got["EnableLogging"] is True


def test_edge_rule_lifecycle(core: CoreClient, zone: PullZoneModel, zone_name: str) -> None:
    zone_id = zone["Id"]
    core.add_or_update_edge_rule(
        zone_id,
        ActionType=SET_RESPONSE_HEADER,
        ActionParameter1="X-Smoke-Test",
        ActionParameter2=zone_name,
        Description=zone_name,
        Enabled=True,
        TriggerMatchingType=MATCH_ANY,
        Triggers=[{"Type": TRIGGER_URL, "PatternMatches": ["*/smoke/*"], "PatternMatchingType": 0}],
    )
    rule = _rule(core, zone_id, zone_name)
    assert rule is not None
    assert rule["Enabled"] is True
    guid = rule["Guid"]
    assert guid

    core.set_edge_rule_enabled(zone_id, guid, enabled=False)
    assert (_rule(core, zone_id, zone_name) or {}).get("Enabled") is False

    rule["ActionParameter2"] = "updated"  # same Guid, so this updates in place
    core.add_or_update_edge_rule(zone_id, **rule)
    assert (_rule(core, zone_id, zone_name) or {}).get("ActionParameter2") == "updated"

    core.delete_edge_rule(zone_id, guid)
    assert _rule(core, zone_id, zone_name) is None


def test_purge(core: CoreClient, zone: PullZoneModel, zone_name: str) -> None:
    core.purge_pull_zone_cache(zone["Id"])
    core.purge_pull_zone_cache(zone["Id"], CacheTag="smoke")
    core.purge_url(f"https://{zone_name}.b-cdn.net/smoke/file.txt")


def test_custom_hostname(core: CoreClient, zone: PullZoneModel, zone_name: str) -> None:
    # .test is reserved (RFC 2606), so no other Bunny account can own it.
    domain = os.environ.get(DOMAIN_VAR, "").strip() or "smoke.test"
    hostname = f"{zone_name}.{domain}"
    core.add_custom_hostname(zone["Id"], hostname)
    names = [h.get("Value") for h in core.get_pull_zone(zone["Id"]).get("Hostnames") or []]
    assert hostname in names
    core.remove_custom_hostname(zone["Id"], hostname)
    names = [h.get("Value") for h in core.get_pull_zone(zone["Id"]).get("Hostnames") or []]
    assert hostname not in names


def test_statistics(core: CoreClient, zone: PullZoneModel) -> None:
    today = datetime.now(tz=UTC).date()
    stats = core.get_statistics(
        pullZone=zone["Id"],
        dateFrom=(today - timedelta(days=1)).isoformat(),
        dateTo=today.isoformat(),
    )
    assert "TotalBandwidthUsed" in stats


def test_logs(logging_client: LoggingClient, zone: PullZoneModel) -> None:
    # A new zone has no traffic yet: this checks auth, routing and the response shape.
    now = datetime.now(tz=UTC)
    page = logging_client.get_logs(
        zone["Id"],
        limit=10,
        **{"from": (now - timedelta(hours=1)).isoformat(), "to": now.isoformat()},
    )
    assert isinstance(page.get("data") or [], list)
    assert "pagination" in page


def test_cli_reads_zone_without_leaking_key(
    api_key: str, zone: PullZoneModel, caplog: pytest.LogCaptureFixture
) -> None:
    runner = CliRunner(env={"BUNNY_API_KEY": ""})
    args = ["--api-key", api_key, "--debug", "--output-format", "json"]
    with caplog.at_level(logging.DEBUG, logger="bunny_cdn_sdk"):
        got = runner.invoke(app, [*args, "pull-zone", "get", str(zone["Id"])])
        rules = runner.invoke(app, [*args, "pull-zone", "edge-rule", "list", str(zone["Id"])])
        missing = runner.invoke(app, [*args, "pull-zone", "get", "1"])  # logs request_failed
    assert got.exit_code == 0, got.output
    assert json.loads(got.stdout)["Id"] == zone["Id"]
    assert rules.exit_code == 0, rules.output
    assert missing.exit_code != 0
    for text in (got.output, rules.output, missing.output, caplog.text):
        assert api_key not in text


def test_zz_delete(core: CoreClient, zone: PullZoneModel) -> None:
    core.delete_pull_zone(zone["Id"])
    with pytest.raises(BunnyNotFoundError):
        core.get_pull_zone(zone["Id"])
