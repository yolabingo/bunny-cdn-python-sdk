"""Tests for ShieldClient: every method's HTTP request, plus paging behavior."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx2
import pytest

from bunny_cdn_sdk.shield import ShieldClient

if TYPE_CHECKING:
    from collections.abc import Callable

BASE = "https://api.bunny.net/shield"


def make_shield_client(handler: Callable[[httpx2.Request], httpx2.Response]) -> ShieldClient:
    return ShieldClient(
        "test_api_key", client=httpx2.Client(transport=httpx2.MockTransport(handler))
    )


def _capture(call: Callable[[ShieldClient], Any]) -> httpx2.Request:
    """Run ``call`` against a mock API and return the single request it sent."""
    sent: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(200, json={})

    call(make_shield_client(handler))
    assert len(sent) == 1
    return sent[0]


# (call, method, path, query, json body or None)
ENDPOINTS: dict[str, tuple[Callable[[ShieldClient], Any], str, str, dict, Any]] = {
    "list_shield_zones": (
        lambda c: c.list_shield_zones(2, 5),
        "GET",
        "/shield-zones",
        {"page": "2", "perPage": "5"},
        None,
    ),
    "get_shield_zone": (lambda c: c.get_shield_zone(1), "GET", "/shield-zone/1", {}, None),
    "get_shield_zone_by_pull_zone": (
        lambda c: c.get_shield_zone_by_pull_zone(9),
        "GET",
        "/shield-zone/get-by-pullzone/9",
        {},
        None,
    ),
    "create_shield_zone": (
        lambda c: c.create_shield_zone(9, learningMode=True),
        "POST",
        "/shield-zone",
        {},
        {"pullZoneId": 9, "shieldZone": {"learningMode": True}},
    ),
    "update_shield_zone": (
        lambda c: c.update_shield_zone(1, learningMode=False),
        "PATCH",
        "/shield-zone",
        {},
        {"shieldZoneId": 1, "shieldZone": {"shieldZoneId": 1, "learningMode": False}},
    ),
    "list_waf_rules": (lambda c: c.list_waf_rules(1), "GET", "/waf/rules/1", {}, None),
    "list_custom_waf_rules": (
        lambda c: c.list_custom_waf_rules(1, 2, 5),
        "GET",
        "/waf/custom-rules/1",
        {"page": "2", "perPage": "5"},
        None,
    ),
    "get_custom_waf_rule": (
        lambda c: c.get_custom_waf_rule(3),
        "GET",
        "/waf/custom-rule/3",
        {},
        None,
    ),
    "create_custom_waf_rule": (
        lambda c: c.create_custom_waf_rule(1, ruleName="r"),
        "POST",
        "/waf/custom-rule",
        {},
        {"shieldZoneId": 1, "ruleName": "r"},
    ),
    "update_custom_waf_rule": (
        lambda c: c.update_custom_waf_rule(3, ruleName="r"),
        "PATCH",
        "/waf/custom-rule/3",
        {},
        {"ruleName": "r"},
    ),
    "delete_custom_waf_rule": (
        lambda c: c.delete_custom_waf_rule(3),
        "DELETE",
        "/waf/custom-rule/3",
        {},
        None,
    ),
    "list_waf_profiles": (lambda c: c.list_waf_profiles(), "GET", "/waf/profiles", {}, None),
    "get_waf_enums": (lambda c: c.get_waf_enums(), "GET", "/waf/enums", {}, None),
    "get_waf_engine_config": (
        lambda c: c.get_waf_engine_config(),
        "GET",
        "/waf/engine-config",
        {},
        None,
    ),
    "list_triggered_waf_rules": (
        lambda c: c.list_triggered_waf_rules(1),
        "GET",
        "/waf/rules/review-triggered/1",
        {},
        None,
    ),
    "review_triggered_waf_rule": (
        lambda c: c.review_triggered_waf_rule(1, "abc", 2),
        "POST",
        "/waf/rules/review-triggered/1",
        {},
        {"ruleId": "abc", "action": 2},
    ),
    "list_rate_limits": (
        lambda c: c.list_rate_limits(1, 2, 5),
        "GET",
        "/rate-limits/1",
        {"page": "2", "perPage": "5"},
        None,
    ),
    "get_rate_limit": (lambda c: c.get_rate_limit(4), "GET", "/rate-limit/4", {}, None),
    "create_rate_limit": (
        lambda c: c.create_rate_limit(1, ruleName="r"),
        "POST",
        "/rate-limit",
        {},
        {"shieldZoneId": 1, "ruleName": "r"},
    ),
    "update_rate_limit": (
        lambda c: c.update_rate_limit(4, ruleName="r"),
        "PATCH",
        "/rate-limit/4",
        {},
        {"ruleName": "r"},
    ),
    "delete_rate_limit": (lambda c: c.delete_rate_limit(4), "DELETE", "/rate-limit/4", {}, None),
    "list_access_lists": (
        lambda c: c.list_access_lists(1),
        "GET",
        "/shield-zone/1/access-lists",
        {},
        None,
    ),
    "get_access_list": (
        lambda c: c.get_access_list(1, 5),
        "GET",
        "/shield-zone/1/access-lists/5",
        {},
        None,
    ),
    "create_access_list": (
        lambda c: c.create_access_list(1, name="n", type=0, content="1.1.1.1"),
        "POST",
        "/shield-zone/1/access-lists",
        {},
        {"name": "n", "type": 0, "content": "1.1.1.1"},
    ),
    "update_access_list": (
        lambda c: c.update_access_list(1, 5, name="n"),
        "PATCH",
        "/shield-zone/1/access-lists/5",
        {},
        {"name": "n"},
    ),
    "update_access_list_configuration": (
        lambda c: c.update_access_list_configuration(1, 5, isEnabled=True),
        "PATCH",
        "/shield-zone/1/access-lists/configurations/5",
        {},
        {"isEnabled": True},
    ),
    "delete_access_list": (
        lambda c: c.delete_access_list(1, 5),
        "DELETE",
        "/shield-zone/1/access-lists/5",
        {},
        None,
    ),
    "get_bot_detection": (
        lambda c: c.get_bot_detection(1),
        "GET",
        "/shield-zone/1/bot-detection",
        {},
        None,
    ),
    "update_bot_detection": (
        lambda c: c.update_bot_detection(1, executionMode=1),
        "PATCH",
        "/shield-zone/1/bot-detection",
        {},
        {"shieldZoneId": 1, "executionMode": 1},
    ),
    "get_event_logs": (
        lambda c: c.get_event_logs(1, "01-31-2026", "tok"),
        "GET",
        "/event-logs/1/01-31-2026/tok",
        {},
        None,
    ),
    "search_event_logs": (
        lambda c: c.search_event_logs(1, query="q", pageSize=10),
        "POST",
        "/event-logs/1/search",
        {},
        {"query": "q", "pageSize": 10},
    ),
    "get_metrics_overview": (
        lambda c: c.get_metrics_overview(1),
        "GET",
        "/metrics/overview/1",
        {},
        None,
    ),
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
    not_endpoints = {"close", "iter_shield_zones", "iter_custom_waf_rules", "iter_rate_limits"}
    public = {n for n in dir(ShieldClient) if not n.startswith("_")} - not_endpoints
    assert public <= ENDPOINTS.keys()


def test_default_base_url_and_trailing_slash() -> None:
    assert ShieldClient("k").base_url == BASE
    assert ShieldClient("k", base_url="https://example.test/").base_url == "https://example.test"


def test_envelope_is_not_unwrapped() -> None:
    envelope = {"data": [{"id": 1}], "page": {"nextPage": None}, "error": None}
    client = make_shield_client(lambda r: httpx2.Response(200, json=envelope))
    assert client.list_shield_zones() == envelope


# ---------------------------------------------------------------------------
# Iterators
# ---------------------------------------------------------------------------


def test_iter_pages_walks_all_pages() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/shield/shield-zones"
        page = int(request.url.params["page"])
        seen.append((request.url.params["page"], request.url.params["perPage"]))
        return httpx2.Response(
            200, json={"data": [{"id": page}], "page": {"nextPage": page + 1 if page < 3 else None}}
        )

    items = list(make_shield_client(handler).iter_shield_zones(per_page=1))
    assert items == [{"id": 1}, {"id": 2}, {"id": 3}]
    assert seen == [("1", "1"), ("2", "1"), ("3", "1")]


def test_iter_pages_single_page() -> None:
    client = make_shield_client(
        lambda r: httpx2.Response(200, json={"data": [{"id": 1}], "page": {"nextPage": None}})
    )
    assert list(client.iter_rate_limits(1)) == [{"id": 1}]


def test_iter_pages_stops_on_empty_data_even_if_next_page_set() -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200, json={"data": [], "page": {"nextPage": 2}})

    assert list(make_shield_client(handler).iter_custom_waf_rules(1)) == []
    assert calls == 1
