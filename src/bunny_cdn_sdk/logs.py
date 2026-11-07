"""Logging API client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bunny_cdn_sdk._client import _BaseClient

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx2

__all__ = ["LoggingClient"]

_BASE_URL = "https://logging.bunnycdn.com"


class LoggingClient(_BaseClient):
    """Bunny CDN Logging API client (v2 pull zone request logs).

    Args:
        api_key: Bunny CDN account API key.
        base_url: Base URL for the Logging API (default: https://logging.bunnycdn.com).
        client: Optional httpx2.Client to inject (advanced use). When provided,
            max_retries is ignored — configure RetryTransport on your client directly.
        max_retries: Number of retry attempts on 429/5xx/network errors (default 0 = no retry).
        backoff_base: Base delay in seconds for exponential backoff (default 0.5).
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = _BASE_URL,
        *,
        client: httpx2.Client | None = None,
        max_retries: int = 0,
        backoff_base: float = 0.5,
    ) -> None:
        super().__init__(api_key, client=client, max_retries=max_retries, backoff_base=backoff_base)
        self.base_url = base_url.rstrip("/")

    def get_logs(self, pull_zone_id: int, **params: Any) -> dict:
        """Get one page of request logs for a pull zone.

        Args:
            pull_zone_id: Pull zone ID.
            **params: Query parameters: ``from`` and ``to`` (ISO-8601 UTC; max 3-day
                range; logs are retained for 3 days), ``status``, ``cacheStatus``,
                ``country``, ``edgeLocation``, ``remoteIp``, ``urlContains``,
                ``userAgentContains``, ``refererContains``, ``search``, ``requestId``,
                ``includeOriginShield``, ``limit`` (max 10000), ``offset`` and
                ``order`` (``asc`` or ``desc``). ``from`` is a Python keyword, so pass
                it as ``get_logs(1, **{"from": "2026-01-01T00:00:00Z"})``.

        Returns:
            Dict with ``data``, ``pagination`` (``offset``, ``limit``, ``returned``,
            ``hasMore``) and ``query``.
        """
        return self._json("GET", f"{self.base_url}/v2/pullzones/{pull_zone_id}/logs", params=params)

    def iter_logs(self, pull_zone_id: int, limit: int = 1000, **params: Any) -> Iterator[dict]:
        """Iterate over every log entry, following offset pagination.

        Args:
            pull_zone_id: Pull zone ID.
            limit: Page size per request (max 10000).
            **params: Same query parameters as :meth:`get_logs`. A supplied ``offset``
                is the starting offset.

        Yields:
            Individual log entry dicts.
        """
        offset = params.pop("offset", 0)
        while True:
            resp = self.get_logs(pull_zone_id, **params, limit=limit, offset=offset)
            yield from resp["data"]
            page = resp["pagination"]
            if not page["hasMore"] or page["returned"] == 0:
                return
            # Pin the window the API resolved, so "now" can't shift between pages.
            params.setdefault("from", resp["query"]["from"])
            params.setdefault("to", resp["query"]["to"])
            offset += page["returned"]
