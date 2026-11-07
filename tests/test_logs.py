"""Tests for LoggingClient."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx2

from bunny_cdn_sdk.logs import LoggingClient

if TYPE_CHECKING:
    from collections.abc import Callable


def make_client(handler: Callable[[httpx2.Request], httpx2.Response]) -> LoggingClient:
    return LoggingClient(
        "test_api_key", client=httpx2.Client(transport=httpx2.MockTransport(handler))
    )


def _pages(pages: list[tuple[list[dict], bool]]) -> tuple[LoggingClient, list[httpx2.Request]]:
    """Client serving ``pages`` in order, plus the list of captured requests."""
    sent: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        data, more = pages[len(sent)]
        sent.append(request)
        pagination = {"returned": len(data), "hasMore": more}
        query = {"from": "2026-01-01T00:00:00Z", "to": "2026-01-02T00:00:00Z"}
        body = {"data": data, "pagination": pagination, "query": query}
        return httpx2.Response(200, json=body)

    return make_client(handler), sent


def test_get_logs_request() -> None:
    client, sent = _pages([([], False)])
    client.get_logs(7, **{"from": "2026-01-01T00:00:00Z"}, status=200)
    req = sent[0]
    assert req.method == "GET"
    assert req.url.path == "/v2/pullzones/7/logs"
    assert req.url.host == "logging.bunnycdn.com"
    assert dict(req.url.params) == {"from": "2026-01-01T00:00:00Z", "status": "200"}
    assert req.headers["AccessKey"] == "test_api_key"


def test_iter_logs_multi_page() -> None:
    client, sent = _pages([([{"i": 1}, {"i": 2}], True), ([{"i": 3}], False)])
    assert list(client.iter_logs(7, limit=2)) == [{"i": 1}, {"i": 2}, {"i": 3}]
    assert [r.url.params["offset"] for r in sent] == ["0", "2"]
    assert all(r.url.params["limit"] == "2" for r in sent)


def test_iter_logs_stops_when_returned_zero() -> None:
    client, sent = _pages([([{"i": 1}], True), ([], True)])
    assert list(client.iter_logs(7)) == [{"i": 1}]
    assert len(sent) == 2


def test_iter_logs_honours_offset() -> None:
    client, sent = _pages([([{"i": 1}], False)])
    assert list(client.iter_logs(7, offset=50)) == [{"i": 1}]
    assert sent[0].url.params["offset"] == "50"


def test_iter_logs_pins_window_after_first_page() -> None:
    client, sent = _pages([([{"i": 1}], True), ([{"i": 2}], False)])
    list(client.iter_logs(7))
    assert "to" not in sent[0].url.params
    assert sent[1].url.params["from"] == "2026-01-01T00:00:00Z"
    assert sent[1].url.params["to"] == "2026-01-02T00:00:00Z"
