"""Tests for PartnerClient: every method's HTTP request, plus the PDF and 204 paths."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx2
import pytest

from bunny_cdn_sdk.partner import PartnerClient

if TYPE_CHECKING:
    from collections.abc import Callable

BASE = "https://api.bunny.net/partner"


def make_partner_client(handler: Callable[[httpx2.Request], httpx2.Response]) -> PartnerClient:
    return PartnerClient(
        "test_api_key", client=httpx2.Client(transport=httpx2.MockTransport(handler))
    )


def _capture(call: Callable[[PartnerClient], Any]) -> httpx2.Request:
    """Run ``call`` against a mock API and return the single request it sent."""
    sent: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(200, json={})

    call(make_partner_client(handler))
    assert len(sent) == 1
    return sent[0]


# (call, method, path, query, json body or None)
ENDPOINTS: dict[str, tuple[Callable[[PartnerClient], Any], str, str, dict, Any]] = {
    "list_customers": (lambda c: c.list_customers(), "GET", "/customers", {}, None),
    "create_customer": (
        lambda c: c.create_customer("a@b.test", FirstName="Ann", Country="US"),
        "POST",
        "/customers",
        {},
        {"Email": "a@b.test", "FirstName": "Ann", "Country": "US"},
    ),
    "invite_customer": (
        lambda c: c.invite_customer("a@b.test"),
        "POST",
        "/customers/invite",
        {},
        {"Email": "a@b.test"},
    ),
    "get_customer_overview": (
        lambda c: c.get_customer_overview("u1"),
        "GET",
        "/customer/u1",
        {},
        None,
    ),
    "get_partner_overview": (lambda c: c.get_partner_overview(), "GET", "/overview", {}, None),
    "get_audit_log": (
        lambda c: c.get_audit_log("u1", "2026-01-31"),
        "GET",
        "/customer/u1/audit/2026-01-31",
        {},
        None,
    ),
    "get_contract": (lambda c: c.get_contract(), "GET", "/contract", {}, None),
    "get_customer_billing": (
        lambda c: c.get_customer_billing("u1"),
        "GET",
        "/customer/u1/billing",
        {},
        None,
    ),
    "download_invoice_pdf": (
        lambda c: c.download_invoice_pdf("u1", 7),
        "GET",
        "/customer/u1/billing/7/pdf",
        {},
        None,
    ),
    "get_customer_pricing": (
        lambda c: c.get_customer_pricing("u1"),
        "GET",
        "/customer/u1/pricing",
        {},
        None,
    ),
    "get_partner_pricing": (lambda c: c.get_partner_pricing(), "GET", "/pricing", {}, None),
    "list_customer_products": (
        lambda c: c.list_customer_products("u1"),
        "GET",
        "/customer/u1/products",
        {},
        None,
    ),
    "set_customer_product": (
        lambda c: c.set_customer_product("u1", 3, enabled=True),
        "PUT",
        "/customer/u1/products/3",
        {"enabled": "true"},
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
    public = {n for n in dir(PartnerClient) if not n.startswith("_")} - {
        "close",
        "iter_audit_log",
    }  # iter_audit_log has its own tests
    assert public <= ENDPOINTS.keys()


def test_default_base_url_and_trailing_slash() -> None:
    assert PartnerClient("k").base_url == BASE
    assert PartnerClient("k", base_url="https://example.test/").base_url == "https://example.test"


def test_audit_log_all_params_with_repeated_arrays() -> None:
    request = _capture(
        lambda c: c.get_audit_log(
            "u1",
            "2026-01-31",
            product=["Cdn", "Dns"],
            resource_type=["PullZone"],
            resource_id=["1", "2"],
            actor_id=["x"],
            order="Descending",
            continuation_token="tok",  # noqa: S106
            limit=50,
        )
    )
    assert request.url.params.multi_items() == [
        ("Product", "Cdn"),
        ("Product", "Dns"),
        ("ResourceType", "PullZone"),
        ("ResourceId", "1"),
        ("ResourceId", "2"),
        ("ActorId", "x"),
        ("Order", "Descending"),
        ("ContinuationToken", "tok"),
        ("Limit", "50"),
    ]


def test_set_customer_product_omits_enabled_when_none() -> None:
    request = _capture(lambda c: c.set_customer_product("u1", 3))
    assert request.url.query == b""


def test_set_customer_product_false_and_204() -> None:
    sent: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(204)

    result = make_partner_client(handler).set_customer_product("u1", 3, enabled=False)
    assert result is None
    assert sent[0].url.params["enabled"] == "false"


def test_download_invoice_pdf_returns_bytes() -> None:
    pdf = b"%PDF-1.7\x00\xff binary"
    client = make_partner_client(lambda r: httpx2.Response(200, content=pdf))
    assert client.download_invoice_pdf("u1", 7) == pdf


def test_iter_audit_log_follows_tokens_and_passes_filters() -> None:
    pages = {
        None: {"Logs": [{"n": 1}, {"n": 2}], "HasMoreData": True, "ContinuationToken": "t1"},
        "t1": {"Logs": [{"n": 3}], "HasMoreData": True, "ContinuationToken": "t2"},
        "t2": {"Logs": [{"n": 4}], "HasMoreData": False, "ContinuationToken": "t3"},
    }
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json=pages[request.url.params.get("ContinuationToken")])

    c = make_partner_client(handler)
    out = list(c.iter_audit_log("u1", "2026-01-31", product=["Cdn"], limit=2))
    assert [e["n"] for e in out] == [1, 2, 3, 4]
    assert len(seen) == 3  # HasMoreData false stops before t3
    assert seen[0].url.path == "/partner/customer/u1/audit/2026-01-31"
    assert seen[0].url.params["Product"] == "Cdn"
    assert seen[0].url.params["Limit"] == "2"


@pytest.mark.parametrize(
    "page",
    [
        {"Logs": [{"n": 1}], "HasMoreData": True, "ContinuationToken": ""},
        {"Logs": [{"n": 1}], "HasMoreData": True},
    ],
)
def test_iter_audit_log_stops_on_empty_token(page: dict) -> None:
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return httpx2.Response(200, json=page)

    assert len(list(make_partner_client(handler).iter_audit_log("u1", "2026-01-31"))) == 1
    assert len(calls) == 1


def test_iter_audit_log_stops_on_empty_logs() -> None:
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return httpx2.Response(
            200, json={"Logs": [], "HasMoreData": True, "ContinuationToken": "again"}
        )

    assert list(make_partner_client(handler).iter_audit_log("u1", "2026-01-31")) == []
    assert len(calls) == 1
