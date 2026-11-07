"""Tests for CoreClient: every method's HTTP request, plus batch and paging behavior."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx2
import pytest

from bunny_cdn_sdk.core import CoreClient

if TYPE_CHECKING:
    from collections.abc import Callable

BASE = "https://api.bunny.net"


def make_core_client(handler: Callable[[httpx2.Request], httpx2.Response]) -> CoreClient:
    return CoreClient("test_api_key", client=httpx2.Client(transport=httpx2.MockTransport(handler)))


def _capture(call: Callable[[CoreClient], Any]) -> httpx2.Request:
    """Run ``call`` against a mock API and return the single request it sent."""
    sent: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(200, json={})

    call(make_core_client(handler))
    assert len(sent) == 1
    return sent[0]


# (call, method, path, query, json body or None)
ENDPOINTS: dict[str, tuple[Callable[[CoreClient], Any], str, str, dict, Any]] = {
    # Edge rules
    "add_or_update_edge_rule": (
        lambda c: c.add_or_update_edge_rule(1, Guid="g", Enabled=True),
        "POST",
        "/pullzone/1/edgerules/addOrUpdate",
        {},
        {"Guid": "g", "Enabled": True},
    ),
    "delete_edge_rule": (
        lambda c: c.delete_edge_rule(1, "g"),
        "DELETE",
        "/pullzone/1/edgerules/g",
        {},
        None,
    ),
    "set_edge_rule_enabled": (
        lambda c: c.set_edge_rule_enabled(1, "g", False),  # noqa: FBT003
        "POST",
        "/pullzone/1/edgerules/g/setEdgeRuleEnabled",
        {},
        {"Id": 1, "Value": False},
    ),
    # Load balancers
    "list_load_balancers": (
        lambda c: c.list_load_balancers(page=2, count=10),
        "GET",
        "/loadbalancer",
        {"page": "2", "count": "10"},
        None,
    ),
    "get_load_balancer": (lambda c: c.get_load_balancer(1), "GET", "/loadbalancer/1", {}, None),
    "create_load_balancer": (
        lambda c: c.create_load_balancer(Name="lb"),
        "POST",
        "/loadbalancer",
        {},
        {"Name": "lb"},
    ),
    "update_load_balancer": (
        lambda c: c.update_load_balancer(1, Name="lb"),
        "POST",
        "/loadbalancer/1",
        {},
        {"Name": "lb"},
    ),
    "delete_load_balancer": (
        lambda c: c.delete_load_balancer(1),
        "DELETE",
        "/loadbalancer/1",
        {},
        None,
    ),
    "add_origin_group": (
        lambda c: c.add_origin_group(1, Name="g"),
        "POST",
        "/loadbalancer/1/origingroup",
        {},
        {"Name": "g"},
    ),
    "update_origin_group": (
        lambda c: c.update_origin_group(1, 2, Name="g"),
        "POST",
        "/loadbalancer/1/origingroup/2",
        {},
        {"Name": "g"},
    ),
    "delete_origin_group": (
        lambda c: c.delete_origin_group(1, 2),
        "DELETE",
        "/loadbalancer/1/origingroup/2",
        {},
        None,
    ),
    "add_origin": (
        lambda c: c.add_origin(1, 2, Address="a"),
        "POST",
        "/loadbalancer/1/origingroup/2/origin",
        {},
        {"Address": "a"},
    ),
    "update_origin": (
        lambda c: c.update_origin(1, 2, 3, Address="a"),
        "POST",
        "/loadbalancer/1/origingroup/2/origin/3",
        {},
        {"Address": "a"},
    ),
    "delete_origin": (
        lambda c: c.delete_origin(1, 2, 3),
        "DELETE",
        "/loadbalancer/1/origingroup/2/origin/3",
        {},
        None,
    ),
    "get_load_balancer_statistics": (
        lambda c: c.get_load_balancer_statistics(1, hourly="true"),
        "GET",
        "/loadbalancer/1/statistics",
        {"hourly": "true"},
        None,
    ),
    "get_load_balancer_pull_zones": (
        lambda c: c.get_load_balancer_pull_zones(1, to="t"),
        "GET",
        "/loadbalancer/1/pullzones",
        {"to": "t"},
        None,
    ),
    "get_load_balancer_account_statistics": (
        lambda c: c.get_load_balancer_account_statistics(**{"from": "f"}),
        "GET",
        "/loadbalancer/statistics",
        {"from": "f"},
        None,
    ),
    "get_load_balancer_usage": (
        lambda c: c.get_load_balancer_usage(1, year=2026, month=1),
        "GET",
        "/loadbalancer/1/usage",
        {"year": "2026", "month": "1"},
        None,
    ),
    # Pull zones
    "list_pull_zones": (
        lambda c: c.list_pull_zones(search="web"),
        "GET",
        "/pullzone",
        {"search": "web"},
        None,
    ),
    "get_pull_zone": (lambda c: c.get_pull_zone(1), "GET", "/pullzone/1", {}, None),
    "create_pull_zone": (
        lambda c: c.create_pull_zone(Name="z"),
        "POST",
        "/pullzone",
        {},
        {"Name": "z"},
    ),
    "update_pull_zone": (
        lambda c: c.update_pull_zone(1, Name="z"),
        "POST",
        "/pullzone/1",
        {},
        {"Name": "z"},
    ),
    "delete_pull_zone": (lambda c: c.delete_pull_zone(1), "DELETE", "/pullzone/1", {}, None),
    "purge_pull_zone_cache": (
        lambda c: c.purge_pull_zone_cache(1),
        "POST",
        "/pullzone/1/purgeCache",
        {},
        None,
    ),
    "purge_pull_zone_cache_tag": (
        lambda c: c.purge_pull_zone_cache(1, CacheTag="t"),
        "POST",
        "/pullzone/1/purgeCache",
        {},
        {"CacheTag": "t"},
    ),
    "add_custom_hostname": (
        lambda c: c.add_custom_hostname(1, "cdn.example.com"),
        "POST",
        "/pullzone/1/addHostname",
        {},
        {"Hostname": "cdn.example.com"},
    ),
    "remove_custom_hostname": (
        lambda c: c.remove_custom_hostname(1, "cdn.example.com"),
        "DELETE",
        "/pullzone/1/removeHostname",
        {},
        {"Hostname": "cdn.example.com"},
    ),
    "add_blocked_ip": (
        lambda c: c.add_blocked_ip(1, "1.2.3.4"),
        "POST",
        "/pullzone/1/addBlockedIp",
        {},
        {"IpAddress": "1.2.3.4"},
    ),
    "remove_blocked_ip": (
        lambda c: c.remove_blocked_ip(1, "1.2.3.4"),
        "POST",
        "/pullzone/1/removeBlockedIp",
        {},
        {"IpAddress": "1.2.3.4"},
    ),
    # Storage zones
    "list_storage_zones": (
        lambda c: c.list_storage_zones(page=2, per_page=5),
        "GET",
        "/storagezone",
        {"page": "2", "perPage": "5"},
        None,
    ),
    "get_storage_zone": (lambda c: c.get_storage_zone(2), "GET", "/storagezone/2", {}, None),
    "create_storage_zone": (
        lambda c: c.create_storage_zone(Name="s"),
        "POST",
        "/storagezone",
        {},
        {"Name": "s"},
    ),
    "update_storage_zone": (
        lambda c: c.update_storage_zone(2, ZoneTier=1),
        "POST",
        "/storagezone/2",
        {},
        {"ZoneTier": 1},
    ),
    "delete_storage_zone": (
        lambda c: c.delete_storage_zone(2),
        "DELETE",
        "/storagezone/2",
        {},
        None,
    ),
    # DNS zones and records
    "list_dns_zones": (
        lambda c: c.list_dns_zones(page=2, per_page=5, search="ex"),
        "GET",
        "/dnszone",
        {"page": "2", "perPage": "5", "search": "ex"},
        None,
    ),
    "get_dns_zone": (lambda c: c.get_dns_zone(3), "GET", "/dnszone/3", {}, None),
    "create_dns_zone": (
        lambda c: c.create_dns_zone(Domain="ex.com"),
        "POST",
        "/dnszone",
        {},
        {"Domain": "ex.com"},
    ),
    "update_dns_zone": (
        lambda c: c.update_dns_zone(3, Ttl=60),
        "POST",
        "/dnszone/3",
        {},
        {"Ttl": 60},
    ),
    "delete_dns_zone": (lambda c: c.delete_dns_zone(3), "DELETE", "/dnszone/3", {}, None),
    "add_dns_record": (
        lambda c: c.add_dns_record(3, Type=0, Name="www"),
        "PUT",
        "/dnszone/3/records",
        {},
        {"Type": 0, "Name": "www"},
    ),
    "update_dns_record": (
        lambda c: c.update_dns_record(3, 9, Value="5.6.7.8"),
        "POST",
        "/dnszone/3/records/9",
        {},
        {"Value": "5.6.7.8"},
    ),
    "delete_dns_record": (
        lambda c: c.delete_dns_record(3, 9),
        "DELETE",
        "/dnszone/3/records/9",
        {},
        None,
    ),
    # Video libraries
    "list_video_libraries": (
        lambda c: c.list_video_libraries(page=2, per_page=5),
        "GET",
        "/videolibrary",
        {"page": "2", "perPage": "5"},
        None,
    ),
    "get_video_library": (lambda c: c.get_video_library(4), "GET", "/videolibrary/4", {}, None),
    "create_video_library": (
        lambda c: c.create_video_library(Name="v"),
        "POST",
        "/videolibrary",
        {},
        {"Name": "v"},
    ),
    "update_video_library": (
        lambda c: c.update_video_library(4, EnableDRM=True),
        "POST",
        "/videolibrary/4",
        {},
        {"EnableDRM": True},
    ),
    "delete_video_library": (
        lambda c: c.delete_video_library(4),
        "DELETE",
        "/videolibrary/4",
        {},
        None,
    ),
    # Utilities
    "purge_url": (
        # The target URL has its own query string; it must arrive as one encoded param.
        lambda c: c.purge_url("https://cdn.example.com/a b.jpg?x=1&y=2", async_="true"),
        "POST",
        "/purge",
        {"url": "https://cdn.example.com/a b.jpg?x=1&y=2", "async_": "true"},
        None,
    ),
    "get_statistics": (
        lambda c: c.get_statistics(pullZone=1, dateFrom="2026-01-01"),
        "GET",
        "/statistics",
        {"pullZone": "1", "dateFrom": "2026-01-01"},
        None,
    ),
    "list_countries": (lambda c: c.list_countries(), "GET", "/country", {}, None),
    "list_regions": (lambda c: c.list_regions(), "GET", "/region", {}, None),
    "get_billing": (lambda c: c.get_billing(), "GET", "/billing", {}, None),
}


@pytest.mark.parametrize(
    ("call", "method", "path", "query", "body"), ENDPOINTS.values(), ids=ENDPOINTS.keys()
)
def test_endpoint_request(call, method: str, path: str, query: dict, body: Any) -> None:
    """Each method sends the exact HTTP method, URL, query and JSON body Bunny expects."""
    request = _capture(call)
    assert request.method == method
    assert str(request.url.copy_with(query=None)) == BASE + path
    assert dict(request.url.params) == query
    assert (json.loads(request.content) if request.content else None) == body
    assert request.headers["AccessKey"] == "test_api_key"


def test_every_public_method_is_covered() -> None:
    """Fails when a new endpoint method is added without a row in ENDPOINTS."""
    not_endpoints = {"close", "get_pull_zones", "iter_dns_zones", "iter_pull_zones"}
    not_endpoints |= {"iter_storage_zones", "iter_video_libraries"}
    public = {n for n in dir(CoreClient) if not n.startswith("_")} - not_endpoints
    assert public <= ENDPOINTS.keys()


def test_returns_parsed_json_body() -> None:
    client = make_core_client(lambda r: httpx2.Response(200, json={"Id": 42}))
    assert client.get_pull_zone(42) == {"Id": 42}


def test_empty_success_body_returns_empty_dict() -> None:
    client = make_core_client(lambda r: httpx2.Response(204))
    assert client.update_dns_record(1, 2, Value="x") == {}


def test_default_base_url_and_trailing_slash() -> None:
    assert CoreClient("k").base_url == BASE
    assert CoreClient("k", base_url="https://example.test/").base_url == "https://example.test"


# ---------------------------------------------------------------------------
# Batch fetch
# ---------------------------------------------------------------------------


def test_get_pull_zones_keeps_input_order() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"Id": int(request.url.path.rsplit("/", 1)[1])})

    assert make_core_client(handler).get_pull_zones([3, 1, 2]) == [{"Id": 3}, {"Id": 1}, {"Id": 2}]


def test_get_pull_zones_empty_list() -> None:
    client = make_core_client(lambda r: httpx2.Response(200, json={}))
    assert client.get_pull_zones([]) == []


# ---------------------------------------------------------------------------
# Iterators
# ---------------------------------------------------------------------------


def test_iter_pull_zones_yields_flat_list() -> None:
    # Without a page param, /pullzone returns a plain array, not a paginated envelope.
    client = make_core_client(lambda r: httpx2.Response(200, json=[{"Id": 1}, {"Id": 2}]))
    assert list(client.iter_pull_zones()) == [{"Id": 1}, {"Id": 2}]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("iter_storage_zones", "/storagezone"),
        ("iter_dns_zones", "/dnszone"),
        ("iter_video_libraries", "/videolibrary"),
    ],
)
def test_paginated_iterators_walk_all_pages(method: str, path: str) -> None:
    pages_seen: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == path
        page = int(request.url.params["page"])
        pages_seen.append(request.url.params["page"])
        return httpx2.Response(
            200,
            json={"Items": [{"Id": page * 10}, {"Id": page * 10 + 1}], "HasMoreItems": page < 3},
        )

    items = list(getattr(make_core_client(handler), method)(per_page=2))
    assert [i["Id"] for i in items] == [10, 11, 20, 21, 30, 31]
    assert pages_seen == ["1", "2", "3"]
