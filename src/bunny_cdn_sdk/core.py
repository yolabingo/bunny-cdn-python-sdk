"""Core API client."""

from __future__ import annotations

import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from bunny_cdn_sdk._client import _BaseClient
from bunny_cdn_sdk._pagination import pagination_iterator

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx

    from bunny_cdn_sdk._types import PaginatedResponse

__all__ = ["CoreClient"]

_BASE_URL = "https://api.bunny.net"


class CoreClient(_BaseClient):
    """Bunny CDN Core API client.

    Wraps the full Bunny CDN Core API surface: Pull Zones, Storage Zones,
    DNS Zones, Video Libraries, and utility endpoints.

    Args:
        api_key: Bunny CDN account API key.
        base_url: Base URL for the Core API (default: https://api.bunnycdn.com).
        client: Optional httpx.Client to inject (advanced use). When provided,
            max_retries is ignored — configure RetryTransport on your client directly.
        max_retries: Number of retry attempts on 429/5xx/network errors (default 0 = no retry).
        backoff_base: Base delay in seconds for exponential backoff (default 0.5).

    Note on concurrent batch operations:
        ``get_pull_zones([id1, id2, ...])`` issues all requests concurrently via
        ``asyncio.gather``. For large ID lists, batch in chunks of 10-20 to stay
        within connection and rate limits.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = _BASE_URL,
        *,
        client: httpx.Client | None = None,
        max_retries: int = 0,
        backoff_base: float = 0.5,
    ) -> None:
        super().__init__(api_key, client=client, max_retries=max_retries, backoff_base=backoff_base)
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Pull Zones — CRUD (CORE-01)
    # ------------------------------------------------------------------

    def list_pull_zones(
        self,
        page: int = 1,
        per_page: int = 1000,
        search: str | None = None,
    ) -> dict:
        """List pull zones (single page).

        Args:
            page: Page number to fetch (default 1).
            per_page: Items per page, 5-1000 (default 1000).
            search: Optional search filter string.

        Returns:
            Paginated response dict with Items, CurrentPage, TotalItems, HasMoreItems.
        """
        params: dict[str, Any] = {"page": page, "perPage": per_page}
        if search is not None:
            params["search"] = search
        return self._sync_request("GET", f"{self.base_url}/pullzone", params=params).json()

    def get_pull_zone(self, id: int) -> dict:
        """Get a single pull zone by ID.

        Args:
            id: Pull zone ID.

        Returns:
            Pull zone dict.
        """
        return self._sync_request("GET", f"{self.base_url}/pullzone/{id}").json()

    def create_pull_zone(self, **kwargs: Any) -> dict:
        """Create a new pull zone.

        Args:
            **kwargs: Pull zone properties (e.g. Name, OriginUrl).

        Returns:
            Created pull zone dict.
        """
        return self._sync_request("POST", f"{self.base_url}/pullzone", json=kwargs).json()

    def update_pull_zone(self, id: int, **kwargs: Any) -> dict:
        """Update an existing pull zone.

        Args:
            id: Pull zone ID.
            **kwargs: Properties to update.

        Returns:
            Updated pull zone dict.
        """
        return self._sync_request("POST", f"{self.base_url}/pullzone/{id}", json=kwargs).json()

    def delete_pull_zone(self, id: int) -> dict:
        """Delete a pull zone.

        Args:
            id: Pull zone ID.

        Returns:
            Response dict (may be empty on success).
        """
        response = self._sync_request("DELETE", f"{self.base_url}/pullzone/{id}")
        return response.json() if response.content else {}

    # ------------------------------------------------------------------
    # Pull Zones — Iterator (CORE-04)
    # ------------------------------------------------------------------

    def iter_pull_zones(
        self,
        per_page: int = 1000,
        search: str | None = None,
    ) -> Iterator[dict]:
        """Iterate over all pull zones, auto-fetching pages as needed.

        Args:
            per_page: Items per page, 5-1000 (default 1000).
            search: Optional search filter string.

        Yields:
            Individual pull zone dicts across all pages.
        """

        def fetch_page(page: int) -> PaginatedResponse:
            params: dict[str, Any] = {"page": page, "perPage": per_page}
            if search is not None:
                params["search"] = search
            return self._request("GET", f"{self.base_url}/pullzone", params=params).json()

        return pagination_iterator(fetch_page)

    # ------------------------------------------------------------------
    # Pull Zones — Concurrent batch fetch (CORE-03)
    # ------------------------------------------------------------------

    def get_pull_zones(self, ids: list[int]) -> list[dict]:
        """Fetch multiple pull zones concurrently.

        Sends all requests in parallel via ThreadPoolExecutor and returns results
        in the same order as the input IDs.

        Note: For large lists, batch in chunks of 10-20 to avoid hitting
        connection and rate limits.

        Args:
            ids: List of pull zone IDs to fetch.

        Returns:
            List of pull zone dicts in the same order as ``ids``.

        Raises:
            Any exception from _request propagates immediately if any request fails.
        """

        def fetch_one(id: int) -> dict:
            return self._request("GET", f"{self.base_url}/pullzone/{id}").json()

        with ThreadPoolExecutor(max_workers=min(len(ids), 20)) as pool:
            return list(pool.map(fetch_one, ids))

    # ------------------------------------------------------------------
    # Pull Zones — Extras (CORE-02)
    # ------------------------------------------------------------------

    def purge_pull_zone_cache(self, id: int, **kwargs: Any) -> dict:
        """Purge the cache for a pull zone.

        Args:
            id: Pull zone ID.
            **kwargs: Optional body params (e.g. files list).

        Returns:
            Response dict.
        """
        response = self._sync_request(
            "POST", f"{self.base_url}/pullzone/{id}/purgeCache", json=kwargs or None
        )
        return response.json() if response.content else {}

    def add_custom_hostname(self, id: int, hostname: str) -> dict:
        """Add a custom hostname to a pull zone.

        Args:
            id: Pull zone ID.
            hostname: Hostname to add (e.g. "cdn.example.com").

        Returns:
            Response dict.
        """
        response = self._sync_request(
            "POST",
            f"{self.base_url}/pullzone/{id}/addHostname",
            json={"Hostname": hostname},
        )
        return response.json() if response.content else {}

    def remove_custom_hostname(self, id: int, hostname: str) -> dict:
        """Remove a custom hostname from a pull zone.

        Args:
            id: Pull zone ID.
            hostname: Hostname to remove.

        Returns:
            Response dict.
        """
        response = self._sync_request(
            "DELETE",
            f"{self.base_url}/pullzone/{id}/removeHostname",
            json={"Hostname": hostname},
        )
        return response.json() if response.content else {}

    def add_blocked_ip(self, id: int, ip: str) -> dict:
        """Block an IP address from a pull zone.

        Args:
            id: Pull zone ID.
            ip: IP address to block.

        Returns:
            Response dict.
        """
        response = self._sync_request(
            "POST",
            f"{self.base_url}/pullzone/{id}/addBlockedIp",
            json={"IpAddress": ip},
        )
        return response.json() if response.content else {}

    def remove_blocked_ip(self, id: int, ip: str) -> dict:
        """Remove a blocked IP address from a pull zone.

        Args:
            id: Pull zone ID.
            ip: IP address to unblock.

        Returns:
            Response dict.
        """
        response = self._sync_request(
            "POST",
            f"{self.base_url}/pullzone/{id}/removeBlockedIp",
            json={"IpAddress": ip},
        )
        return response.json() if response.content else {}

    # ------------------------------------------------------------------
    # Storage Zones — CRUD + Iterator (CORE-05, CORE-06)
    # ------------------------------------------------------------------

    def list_storage_zones(self, page: int = 1, per_page: int = 1000) -> dict:
        """List storage zones (single page).

        Args:
            page: Page number (default 1).
            per_page: Items per page, 5-1000 (default 1000).

        Returns:
            Paginated response dict.
        """
        params: dict[str, Any] = {"page": page, "perPage": per_page}
        return self._sync_request("GET", f"{self.base_url}/storagezone", params=params).json()

    def get_storage_zone(self, id: int) -> dict:
        """Get a storage zone by ID.

        Args:
            id: Storage zone ID.

        Returns:
            Storage zone dict.
        """
        return self._sync_request("GET", f"{self.base_url}/storagezone/{id}").json()

    def create_storage_zone(self, **kwargs: Any) -> dict:
        """Create a new storage zone.

        Args:
            **kwargs: Storage zone properties (e.g. Name, Region).

        Returns:
            Created storage zone dict.
        """
        return self._sync_request("POST", f"{self.base_url}/storagezone", json=kwargs).json()

    def update_storage_zone(self, id: int, **kwargs: Any) -> dict:
        """Update an existing storage zone.

        Args:
            id: Storage zone ID.
            **kwargs: Properties to update.

        Returns:
            Updated storage zone dict.
        """
        return self._sync_request("POST", f"{self.base_url}/storagezone/{id}", json=kwargs).json()

    def delete_storage_zone(self, id: int) -> dict:
        """Delete a storage zone.

        Args:
            id: Storage zone ID.

        Returns:
            Response dict (may be empty on success).
        """
        response = self._sync_request("DELETE", f"{self.base_url}/storagezone/{id}")
        return response.json() if response.content else {}

    def iter_storage_zones(self, per_page: int = 1000) -> Iterator[dict]:
        """Iterate over all storage zones, auto-fetching pages as needed.

        Args:
            per_page: Items per page, 5-1000 (default 1000).

        Yields:
            Individual storage zone dicts across all pages.
        """

        def fetch_page(page: int) -> PaginatedResponse:
            params: dict[str, Any] = {"page": page, "perPage": per_page}
            return self._request("GET", f"{self.base_url}/storagezone", params=params).json()

        return pagination_iterator(fetch_page)

    # ------------------------------------------------------------------
    # DNS Zones — CRUD + Iterator (CORE-07, CORE-09)
    # ------------------------------------------------------------------

    def list_dns_zones(
        self,
        page: int = 1,
        per_page: int = 1000,
        search: str | None = None,
    ) -> dict:
        """List DNS zones (single page).

        Args:
            page: Page number (default 1).
            per_page: Items per page, 5-1000 (default 1000).
            search: Optional search filter string.

        Returns:
            Paginated response dict.
        """
        params: dict[str, Any] = {"page": page, "perPage": per_page}
        if search is not None:
            params["search"] = search
        return self._sync_request("GET", f"{self.base_url}/dnszone", params=params).json()

    def get_dns_zone(self, id: int) -> dict:
        """Get a DNS zone by ID.

        Args:
            id: DNS zone ID.

        Returns:
            DNS zone dict.
        """
        return self._sync_request("GET", f"{self.base_url}/dnszone/{id}").json()

    def create_dns_zone(self, **kwargs: Any) -> dict:
        """Create a new DNS zone.

        Args:
            **kwargs: DNS zone properties (e.g. Domain).

        Returns:
            Created DNS zone dict.
        """
        return self._sync_request("POST", f"{self.base_url}/dnszone", json=kwargs).json()

    def update_dns_zone(self, id: int, **kwargs: Any) -> dict:
        """Update an existing DNS zone.

        Args:
            id: DNS zone ID.
            **kwargs: Properties to update.

        Returns:
            Updated DNS zone dict.
        """
        return self._sync_request("POST", f"{self.base_url}/dnszone/{id}", json=kwargs).json()

    def delete_dns_zone(self, id: int) -> dict:
        """Delete a DNS zone.

        Args:
            id: DNS zone ID.

        Returns:
            Response dict (may be empty on success).
        """
        response = self._sync_request("DELETE", f"{self.base_url}/dnszone/{id}")
        return response.json() if response.content else {}

    def iter_dns_zones(
        self,
        per_page: int = 1000,
        search: str | None = None,
    ) -> Iterator[dict]:
        """Iterate over all DNS zones, auto-fetching pages as needed.

        Args:
            per_page: Items per page, 5-1000 (default 1000).
            search: Optional search filter string.

        Yields:
            Individual DNS zone dicts across all pages.
        """

        def fetch_page(page: int) -> PaginatedResponse:
            params: dict[str, Any] = {"page": page, "perPage": per_page}
            if search is not None:
                params["search"] = search
            return self._request("GET", f"{self.base_url}/dnszone", params=params).json()

        return pagination_iterator(fetch_page)

    # ------------------------------------------------------------------
    # DNS Records (CORE-08)
    # ------------------------------------------------------------------

    def add_dns_record(self, zone_id: int, **kwargs: Any) -> dict:
        """Add a DNS record to a zone.

        Args:
            zone_id: DNS zone ID.
            **kwargs: DNS record properties (e.g. Type, Name, Value, Ttl).

        Returns:
            Created DNS record dict.
        """
        return self._sync_request(
            "PUT", f"{self.base_url}/dnszone/{zone_id}/records", json=kwargs
        ).json()

    def update_dns_record(self, zone_id: int, record_id: int, **kwargs: Any) -> dict:
        """Update a DNS record within a zone.

        Args:
            zone_id: DNS zone ID.
            record_id: DNS record ID.
            **kwargs: Properties to update.

        Returns:
            Updated DNS record dict.
        """
        return self._sync_request(
            "POST",
            f"{self.base_url}/dnszone/{zone_id}/records/{record_id}",
            json=kwargs,
        ).json()

    def delete_dns_record(self, zone_id: int, record_id: int) -> dict:
        """Delete a DNS record from a zone.

        Args:
            zone_id: DNS zone ID.
            record_id: DNS record ID.

        Returns:
            Response dict (may be empty on success).
        """
        response = self._sync_request(
            "DELETE", f"{self.base_url}/dnszone/{zone_id}/records/{record_id}"
        )
        return response.json() if response.content else {}

    # ------------------------------------------------------------------
    # Video Libraries — CRUD (CORE-10)
    # ------------------------------------------------------------------

    def list_video_libraries(self, page: int = 1, per_page: int = 1000) -> dict:
        """List video libraries (single page).

        Args:
            page: Page number (default 1).
            per_page: Items per page, 5-1000 (default 1000).

        Returns:
            Paginated response dict.
        """
        params: dict[str, Any] = {"page": page, "perPage": per_page}
        return self._sync_request("GET", f"{self.base_url}/videolibrary", params=params).json()

    def get_video_library(self, id: int) -> dict:
        """Get a video library by ID.

        Args:
            id: Video library ID.

        Returns:
            Video library dict.
        """
        return self._sync_request("GET", f"{self.base_url}/videolibrary/{id}").json()

    def create_video_library(self, **kwargs: Any) -> dict:
        """Create a new video library.

        Args:
            **kwargs: Video library properties (e.g. Name).

        Returns:
            Created video library dict.
        """
        return self._sync_request("POST", f"{self.base_url}/videolibrary", json=kwargs).json()

    def update_video_library(self, id: int, **kwargs: Any) -> dict:
        """Update a video library.

        Args:
            id: Video library ID.
            **kwargs: Properties to update.

        Returns:
            Updated video library dict.
        """
        return self._sync_request("POST", f"{self.base_url}/videolibrary/{id}", json=kwargs).json()

    def delete_video_library(self, id: int) -> dict:
        """Delete a video library.

        Args:
            id: Video library ID.

        Returns:
            Response dict (may be empty on success).
        """
        response = self._sync_request("DELETE", f"{self.base_url}/videolibrary/{id}")
        return response.json() if response.content else {}

    def iter_video_libraries(self, per_page: int = 1000) -> Iterator[dict]:
        """Iterate over all video libraries, auto-fetching pages as needed.

        Args:
            per_page: Items per page, 5-1000 (default 1000).

        Yields:
            Individual video library dicts across all pages.
        """

        def fetch_page(page: int) -> PaginatedResponse:
            params: dict[str, Any] = {"page": page, "perPage": per_page}
            return self._request("GET", f"{self.base_url}/videolibrary", params=params).json()

        return pagination_iterator(fetch_page)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def purge_url(self, url: str, **kwargs: Any) -> dict:
        """Purge a specific URL from the CDN cache.

        Args:
            url: The full URL to purge (e.g. "https://cdn.example.com/image.jpg").
            **kwargs: Additional query params passed to the purge endpoint.

        Returns:
            Response dict.
        """
        encoded_url = urllib.parse.quote(url, safe="")
        query = f"url={encoded_url}"
        if kwargs:
            extra = urllib.parse.urlencode(kwargs)
            query = f"{query}&{extra}"
        response = self._sync_request("POST", f"{self.base_url}/purge?{query}")
        return response.json() if response.content else {}

    def get_statistics(self, **kwargs: Any) -> dict:
        """Get CDN statistics.

        Args:
            **kwargs: Optional query params (e.g. dateFrom, dateTo, pullZoneId).

        Returns:
            Statistics dict.
        """
        return self._sync_request("GET", f"{self.base_url}/statistics", params=kwargs).json()

    def list_countries(self) -> dict:
        """List available countries.

        Returns:
            Response dict containing country list.
        """
        return self._sync_request("GET", f"{self.base_url}/country").json()

    def list_regions(self) -> dict:
        """List available CDN regions.

        Returns:
            Response dict containing region list.
        """
        return self._sync_request("GET", f"{self.base_url}/region").json()

    def get_billing(self) -> dict:
        """Get billing information for the account.

        Returns:
            Billing info dict.
        """
        return self._sync_request("GET", f"{self.base_url}/billing").json()
