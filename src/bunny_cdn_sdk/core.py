"""Core API client."""

from __future__ import annotations

import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Unpack

from bunny_cdn_sdk._client import _BaseClient
from bunny_cdn_sdk._pagination import pagination_iterator
from bunny_cdn_sdk.models.core import (
    AddDnsRecordModel,
    BillingModel,
    CountriesPublicGetCountryListResponse,
    DnsRecordModel,
    DnsZoneAddModel,
    DnsZoneModel,
    EdgeRuleV2Model,
    LoadBalancerOriginCreateModel,
    LoadBalancerOriginGroupModel,
    LoadBalancerOriginModel,
    LoadBalancerProfileEndpointGetLoadBalancersResponse,
    LoadBalancerProfileModel,
    LoadBalancerSettingsModel,
    LoadBalancerStatisticsEndpointGetAttachedPullZonesResponse,
    LoadBalancerStatisticsEndpointGetLoadBalancerAccountStatisticsResponse,
    LoadBalancerStatisticsModel,
    LoadBalancerUsageModel,
    OriginGroupCreateModel,
    PaginationListModelOfDnsZoneModel,
    PaginationListModelOfVideoLibraryModel,
    PullZoneAddModel,
    PullZoneModel,
    PullZonePublicIndexAllResponse,
    PullZonePurgeModel,
    PullZoneSettingsModel,
    RegionPublicIndexResponse,
    StatisticsModel,
    StorageZoneModel,
    StorageZoneModelAdd,
    StorageZoneSettingsModel,
    UpdateDnsRecordModel,
    UpdateDnsZoneModel,
    VideoLibraryCreateModel,
    VideoLibraryModel,
    VideoLibraryUpdateModel,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    import httpx2
__all__ = ["CoreClient"]

_BASE_URL = "https://api.bunny.net"


class CoreClient(_BaseClient):
    """Bunny CDN Core API client.

    Wraps the full Bunny CDN Core API surface: Pull Zones, Storage Zones,
    DNS Zones, Video Libraries, Edge Rules, Load Balancers, and utility endpoints.

    Args:
        api_key: Bunny CDN account API key.
        base_url: Base URL for the Core API (default: https://api.bunny.net).
        client: Optional httpx2.Client to inject (advanced use). When provided,
            max_retries is ignored — configure RetryTransport on your client directly.
        max_retries: Number of retry attempts on 429/5xx/network errors (default 0 = no retry).
        backoff_base: Base delay in seconds for exponential backoff (default 0.5).

    Note on concurrent batch operations:
        ``get_pull_zones([id1, id2, ...])`` fetches up to 20 zones at a time on a
        thread pool.
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

    # ------------------------------------------------------------------
    # Pull Zones — CRUD (CORE-01)
    # ------------------------------------------------------------------

    def list_pull_zones(self, search: str | None = None) -> PullZonePublicIndexAllResponse:
        """List all pull zones.

        Args:
            search: Optional search filter string.

        Returns:
            List of pull zone dicts. Without a ``page`` param the API returns every
            zone as one flat list, so no paging is needed.
        """
        if search is None:
            return self._json(
                "GET", f"{self.base_url}/pullzone", expect=PullZonePublicIndexAllResponse
            )
        # With search, the live API answers with a paginated envelope (Items, HasMoreItems)
        # instead of the documented plain array, so page through it explicitly.
        return list(self._iter_paged("/pullzone", 1000, search=search))

    def get_pull_zone(self, id: int) -> PullZoneModel:
        """Get a single pull zone by ID.

        Args:
            id: Pull zone ID.

        Returns:
            Pull zone dict.
        """
        return self._json("GET", f"{self.base_url}/pullzone/{id}", expect=PullZoneModel)

    def create_pull_zone(self, **kwargs: Unpack[PullZoneAddModel]) -> dict:
        """Create a new pull zone.

        Args:
            **kwargs: Pull zone properties (e.g. Name, OriginUrl).

        Returns:
            Created pull zone dict.
        """
        return self._json("POST", f"{self.base_url}/pullzone", json=kwargs)

    def update_pull_zone(self, id: int, **kwargs: Unpack[PullZoneSettingsModel]) -> PullZoneModel:
        """Update an existing pull zone.

        Args:
            id: Pull zone ID.
            **kwargs: Properties to update.

        Returns:
            Updated pull zone dict.
        """
        return self._json(
            "POST", f"{self.base_url}/pullzone/{id}", json=kwargs, expect=PullZoneModel
        )

    def delete_pull_zone(self, id: int) -> dict:
        """Delete a pull zone.

        Args:
            id: Pull zone ID.

        Returns:
            Response dict (may be empty on success).
        """
        return self._json("DELETE", f"{self.base_url}/pullzone/{id}")

    # ------------------------------------------------------------------
    # Pull Zones — Iterator (CORE-04)
    # ------------------------------------------------------------------

    def iter_pull_zones(self, search: str | None = None) -> Iterator[PullZoneModel]:
        """Iterate over all pull zones.

        Args:
            search: Optional search filter string.

        Yields:
            Individual pull zone dicts.
        """
        yield from self.list_pull_zones(search=search)

    # ------------------------------------------------------------------
    # Pull Zones — Concurrent batch fetch (CORE-03)
    # ------------------------------------------------------------------

    def get_pull_zones(self, ids: list[int]) -> list[PullZoneModel]:
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
            Any SDK error from the first failed request.
        """

        def fetch_one(id: int) -> PullZoneModel:
            return self._json("GET", f"{self.base_url}/pullzone/{id}", expect=PullZoneModel)

        with ThreadPoolExecutor(max_workers=max(1, min(len(ids), 20))) as pool:
            return list(pool.map(fetch_one, ids))

    # ------------------------------------------------------------------
    # Pull Zones — Extras (CORE-02)
    # ------------------------------------------------------------------

    def purge_pull_zone_cache(self, id: int, **kwargs: Unpack[PullZonePurgeModel]) -> dict:
        """Purge the cache for a pull zone.

        Args:
            id: Pull zone ID.
            **kwargs: Optional body params (e.g. files list).

        Returns:
            Response dict.
        """
        return self._json("POST", f"{self.base_url}/pullzone/{id}/purgeCache", json=kwargs or None)

    def add_custom_hostname(self, id: int, hostname: str) -> dict:
        """Add a custom hostname to a pull zone.

        Args:
            id: Pull zone ID.
            hostname: Hostname to add (e.g. "cdn.example.com").

        Returns:
            Response dict.
        """
        return self._json(
            "POST",
            f"{self.base_url}/pullzone/{id}/addHostname",
            json={"Hostname": hostname},
        )

    def remove_custom_hostname(self, id: int, hostname: str) -> dict:
        """Remove a custom hostname from a pull zone.

        Args:
            id: Pull zone ID.
            hostname: Hostname to remove.

        Returns:
            Response dict.
        """
        return self._json(
            "DELETE",
            f"{self.base_url}/pullzone/{id}/removeHostname",
            json={"Hostname": hostname},
        )

    def add_blocked_ip(self, id: int, ip: str) -> dict:
        """Block an IP address from a pull zone.

        Args:
            id: Pull zone ID.
            ip: IP address to block.

        Returns:
            Response dict.
        """
        return self._json(
            "POST",
            f"{self.base_url}/pullzone/{id}/addBlockedIp",
            json={"IpAddress": ip},
        )

    def remove_blocked_ip(self, id: int, ip: str) -> dict:
        """Remove a blocked IP address from a pull zone.

        Args:
            id: Pull zone ID.
            ip: IP address to unblock.

        Returns:
            Response dict.
        """
        return self._json(
            "POST",
            f"{self.base_url}/pullzone/{id}/removeBlockedIp",
            json={"IpAddress": ip},
        )

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
        return self._json("GET", f"{self.base_url}/storagezone", params=params)

    def get_storage_zone(self, id: int) -> StorageZoneModel:
        """Get a storage zone by ID.

        Args:
            id: Storage zone ID.

        Returns:
            Storage zone dict.
        """
        return self._json("GET", f"{self.base_url}/storagezone/{id}", expect=StorageZoneModel)

    def create_storage_zone(self, **kwargs: Unpack[StorageZoneModelAdd]) -> StorageZoneModel:
        """Create a new storage zone.

        Args:
            **kwargs: Storage zone properties (e.g. Name, Region).

        Returns:
            Created storage zone dict.
        """
        return self._json(
            "POST", f"{self.base_url}/storagezone", json=kwargs, expect=StorageZoneModel
        )

    def update_storage_zone(self, id: int, **kwargs: Unpack[StorageZoneSettingsModel]) -> dict:
        """Update an existing storage zone.

        Args:
            id: Storage zone ID.
            **kwargs: Properties to update.

        Returns:
            Updated storage zone dict.
        """
        return self._json("POST", f"{self.base_url}/storagezone/{id}", json=kwargs)

    def delete_storage_zone(self, id: int) -> dict:
        """Delete a storage zone.

        Args:
            id: Storage zone ID.

        Returns:
            Response dict (may be empty on success).
        """
        return self._json("DELETE", f"{self.base_url}/storagezone/{id}")

    def _iter_paged(
        self, path: str, per_page: int, expect: Any = None, **params: Any
    ) -> Iterator[Any]:
        def fetch_page(page: int) -> Mapping[str, Any]:
            query = {"page": page, "perPage": per_page, **params}
            return self._json("GET", f"{self.base_url}{path}", params=query, expect=expect)

        return pagination_iterator(fetch_page)

    def iter_storage_zones(self, per_page: int = 1000) -> Iterator[StorageZoneModel]:
        """Iterate over all storage zones, auto-fetching pages as needed.

        Args:
            per_page: Items per page, 5-1000 (default 1000).

        Yields:
            Individual storage zone dicts across all pages.
        """

        return self._iter_paged("/storagezone", per_page)

    # ------------------------------------------------------------------
    # DNS Zones — CRUD + Iterator (CORE-07, CORE-09)
    # ------------------------------------------------------------------

    def list_dns_zones(
        self,
        page: int = 1,
        per_page: int = 1000,
        search: str | None = None,
    ) -> PaginationListModelOfDnsZoneModel:
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
        return self._json(
            "GET",
            f"{self.base_url}/dnszone",
            params=params,
            expect=PaginationListModelOfDnsZoneModel,
        )

    def get_dns_zone(self, id: int) -> DnsZoneModel:
        """Get a DNS zone by ID.

        Args:
            id: DNS zone ID.

        Returns:
            DNS zone dict.
        """
        return self._json("GET", f"{self.base_url}/dnszone/{id}", expect=DnsZoneModel)

    def create_dns_zone(self, **kwargs: Unpack[DnsZoneAddModel]) -> dict:
        """Create a new DNS zone.

        Args:
            **kwargs: DNS zone properties (e.g. Domain).

        Returns:
            Created DNS zone dict.
        """
        return self._json("POST", f"{self.base_url}/dnszone", json=kwargs)

    def update_dns_zone(self, id: int, **kwargs: Unpack[UpdateDnsZoneModel]) -> DnsZoneModel:
        """Update an existing DNS zone.

        Args:
            id: DNS zone ID.
            **kwargs: Properties to update.

        Returns:
            Updated DNS zone dict.
        """
        return self._json("POST", f"{self.base_url}/dnszone/{id}", json=kwargs, expect=DnsZoneModel)

    def delete_dns_zone(self, id: int) -> dict:
        """Delete a DNS zone.

        Args:
            id: DNS zone ID.

        Returns:
            Response dict (may be empty on success).
        """
        return self._json("DELETE", f"{self.base_url}/dnszone/{id}")

    def iter_dns_zones(
        self,
        per_page: int = 1000,
        search: str | None = None,
    ) -> Iterator[DnsZoneModel]:
        """Iterate over all DNS zones, auto-fetching pages as needed.

        Args:
            per_page: Items per page, 5-1000 (default 1000).
            search: Optional search filter string.

        Yields:
            Individual DNS zone dicts across all pages.
        """

        return self._iter_paged(
            "/dnszone",
            per_page,
            PaginationListModelOfDnsZoneModel,
            **({"search": search} if search is not None else {}),
        )

    # ------------------------------------------------------------------
    # DNS Records (CORE-08)
    # ------------------------------------------------------------------

    def add_dns_record(self, zone_id: int, **kwargs: Unpack[AddDnsRecordModel]) -> DnsRecordModel:
        """Add a DNS record to a zone.

        Args:
            zone_id: DNS zone ID.
            **kwargs: DNS record properties (e.g. Type, Name, Value, Ttl).

        Returns:
            Created DNS record dict.
        """
        return self._json(
            "PUT", f"{self.base_url}/dnszone/{zone_id}/records", json=kwargs, expect=DnsRecordModel
        )

    def update_dns_record(
        self, zone_id: int, record_id: int, **kwargs: Unpack[UpdateDnsRecordModel]
    ) -> dict:
        """Update a DNS record within a zone.

        Args:
            zone_id: DNS zone ID.
            record_id: DNS record ID.
            **kwargs: Properties to update.

        Returns:
            Updated DNS record dict.
        """
        return self._json(
            "POST",
            f"{self.base_url}/dnszone/{zone_id}/records/{record_id}",
            json=kwargs,
        )

    def delete_dns_record(self, zone_id: int, record_id: int) -> dict:
        """Delete a DNS record from a zone.

        Args:
            zone_id: DNS zone ID.
            record_id: DNS record ID.

        Returns:
            Response dict (may be empty on success).
        """
        return self._json("DELETE", f"{self.base_url}/dnszone/{zone_id}/records/{record_id}")

    # ------------------------------------------------------------------
    # Video Libraries — CRUD (CORE-10)
    # ------------------------------------------------------------------

    def list_video_libraries(
        self, page: int = 1, per_page: int = 1000
    ) -> PaginationListModelOfVideoLibraryModel:
        """List video libraries (single page).

        Args:
            page: Page number (default 1).
            per_page: Items per page, 5-1000 (default 1000).

        Returns:
            Paginated response dict.
        """
        params: dict[str, Any] = {"page": page, "perPage": per_page}
        return self._json(
            "GET",
            f"{self.base_url}/videolibrary",
            params=params,
            expect=PaginationListModelOfVideoLibraryModel,
        )

    def get_video_library(self, id: int) -> VideoLibraryModel:
        """Get a video library by ID.

        Args:
            id: Video library ID.

        Returns:
            Video library dict.
        """
        return self._json("GET", f"{self.base_url}/videolibrary/{id}", expect=VideoLibraryModel)

    def create_video_library(self, **kwargs: Unpack[VideoLibraryCreateModel]) -> VideoLibraryModel:
        """Create a new video library.

        Args:
            **kwargs: Video library properties (e.g. Name).

        Returns:
            Created video library dict.
        """
        return self._json(
            "POST", f"{self.base_url}/videolibrary", json=kwargs, expect=VideoLibraryModel
        )

    def update_video_library(
        self, id: int, **kwargs: Unpack[VideoLibraryUpdateModel]
    ) -> VideoLibraryModel:
        """Update a video library.

        Args:
            id: Video library ID.
            **kwargs: Properties to update.

        Returns:
            Updated video library dict.
        """
        return self._json(
            "POST", f"{self.base_url}/videolibrary/{id}", json=kwargs, expect=VideoLibraryModel
        )

    def delete_video_library(self, id: int) -> dict:
        """Delete a video library.

        Args:
            id: Video library ID.

        Returns:
            Response dict (may be empty on success).
        """
        return self._json("DELETE", f"{self.base_url}/videolibrary/{id}")

    def iter_video_libraries(self, per_page: int = 1000) -> Iterator[VideoLibraryModel]:
        """Iterate over all video libraries, auto-fetching pages as needed.

        Args:
            per_page: Items per page, 5-1000 (default 1000).

        Yields:
            Individual video library dicts across all pages.
        """

        return self._iter_paged("/videolibrary", per_page, PaginationListModelOfVideoLibraryModel)

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
        return self._json("POST", f"{self.base_url}/purge?{query}")

    def get_statistics(self, **kwargs: Any) -> StatisticsModel:
        """Get CDN statistics.

        Args:
            **kwargs: Optional query params (e.g. dateFrom, dateTo, pullZone).

        Returns:
            Statistics dict.
        """
        return self._json(
            "GET", f"{self.base_url}/statistics", params=kwargs, expect=StatisticsModel
        )

    def list_countries(self) -> CountriesPublicGetCountryListResponse:
        """List available countries.

        Returns:
            List of country dicts with Name, IsoCode, IsEU, TaxRate, TaxPrefix fields.
        """
        return self._json(
            "GET", f"{self.base_url}/country", expect=CountriesPublicGetCountryListResponse
        )

    def list_regions(self) -> RegionPublicIndexResponse:
        """List available CDN regions.

        Returns:
            List of region dicts with Id, Name, PricePerGigabyte, RegionCode, ContinentCode fields.
        """
        return self._json("GET", f"{self.base_url}/region", expect=RegionPublicIndexResponse)

    def get_billing(self) -> BillingModel:
        """Get billing information for the account.

        Returns:
            Billing info dict.
        """
        return self._json("GET", f"{self.base_url}/billing", expect=BillingModel)

    # ------------------------------------------------------------------
    # Edge Rules
    # ------------------------------------------------------------------

    def add_or_update_edge_rule(self, pull_zone_id: int, **kwargs: Unpack[EdgeRuleV2Model]) -> dict:
        """Create or update an edge rule on a pull zone.

        Edge rules have no list endpoint; read them from ``get_pull_zone(id)["EdgeRules"]``.

        Args:
            pull_zone_id: Pull zone ID.
            **kwargs: Edge rule fields (e.g. ActionType, Triggers). Include ``Guid`` to update.

        Returns:
            Response dict.
        """
        return self._json(
            "POST", f"{self.base_url}/pullzone/{pull_zone_id}/edgerules/addOrUpdate", json=kwargs
        )

    def delete_edge_rule(self, pull_zone_id: int, edge_rule_id: str) -> dict:
        """Delete an edge rule.

        Args:
            pull_zone_id: Pull zone ID.
            edge_rule_id: Edge rule GUID.

        Returns:
            Response dict.
        """
        return self._json(
            "DELETE", f"{self.base_url}/pullzone/{pull_zone_id}/edgerules/{edge_rule_id}"
        )

    def set_edge_rule_enabled(self, pull_zone_id: int, edge_rule_id: str, enabled: bool) -> dict:  # noqa: FBT001
        """Enable or disable an edge rule.

        Args:
            pull_zone_id: Pull zone ID.
            edge_rule_id: Edge rule GUID.
            enabled: True to enable the rule, False to disable it.

        Returns:
            Response dict.
        """
        return self._json(
            "POST",
            f"{self.base_url}/pullzone/{pull_zone_id}/edgerules/{edge_rule_id}/setEdgeRuleEnabled",
            json={"Id": pull_zone_id, "Value": enabled},
        )

    # ------------------------------------------------------------------
    # Load Balancers
    # ------------------------------------------------------------------

    def list_load_balancers(
        self, page: int = 1, count: int = 50
    ) -> LoadBalancerProfileEndpointGetLoadBalancersResponse:
        """List load balancers.

        Args:
            page: Page number (default 1).
            count: Items per page (default 50).

        Returns:
            List of load balancer dicts.
        """
        return self._json(
            "GET",
            f"{self.base_url}/loadbalancer",
            params={"page": page, "count": count},
            expect=LoadBalancerProfileEndpointGetLoadBalancersResponse,
        )

    def get_load_balancer(self, id: int) -> LoadBalancerProfileModel:
        """Get a load balancer.

        Args:
            id: Load balancer ID.

        Returns:
            Response dict.
        """
        return self._json(
            "GET", f"{self.base_url}/loadbalancer/{id}", expect=LoadBalancerProfileModel
        )

    def create_load_balancer(
        self, **kwargs: Unpack[LoadBalancerSettingsModel]
    ) -> LoadBalancerProfileModel:
        """Create a load balancer.

        Args:
            **kwargs: Load balancer fields (e.g. Name).

        Returns:
            Response dict.
        """
        return self._json(
            "POST", f"{self.base_url}/loadbalancer", json=kwargs, expect=LoadBalancerProfileModel
        )

    def update_load_balancer(
        self, id: int, **kwargs: Unpack[LoadBalancerSettingsModel]
    ) -> LoadBalancerProfileModel:
        """Update a load balancer.

        Args:
            id: Load balancer ID.
            **kwargs: Fields to update.

        Returns:
            Response dict.
        """
        return self._json(
            "POST",
            f"{self.base_url}/loadbalancer/{id}",
            json=kwargs,
            expect=LoadBalancerProfileModel,
        )

    def delete_load_balancer(self, id: int) -> dict:
        """Delete a load balancer.

        Args:
            id: Load balancer ID.

        Returns:
            Response dict.
        """
        return self._json("DELETE", f"{self.base_url}/loadbalancer/{id}")

    def add_origin_group(
        self, lb_id: int, **kwargs: Unpack[OriginGroupCreateModel]
    ) -> LoadBalancerOriginGroupModel:
        """Add an origin group to a load balancer.

        Args:
            lb_id: Load balancer ID.
            **kwargs: Origin group fields.

        Returns:
            Response dict.
        """
        return self._json(
            "POST",
            f"{self.base_url}/loadbalancer/{lb_id}/origingroup",
            json=kwargs,
            expect=LoadBalancerOriginGroupModel,
        )

    def update_origin_group(
        self, lb_id: int, group_id: int, **kwargs: Unpack[OriginGroupCreateModel]
    ) -> LoadBalancerOriginGroupModel:
        """Update an origin group.

        Args:
            lb_id: Load balancer ID.
            group_id: Origin group ID.
            **kwargs: Fields to update.

        Returns:
            Response dict.
        """
        return self._json(
            "POST",
            f"{self.base_url}/loadbalancer/{lb_id}/origingroup/{group_id}",
            json=kwargs,
            expect=LoadBalancerOriginGroupModel,
        )

    def delete_origin_group(self, lb_id: int, group_id: int) -> dict:
        """Delete an origin group.

        Args:
            lb_id: Load balancer ID.
            group_id: Origin group ID.

        Returns:
            Response dict.
        """
        return self._json("DELETE", f"{self.base_url}/loadbalancer/{lb_id}/origingroup/{group_id}")

    def add_origin(
        self, lb_id: int, group_id: int, **kwargs: Unpack[LoadBalancerOriginCreateModel]
    ) -> LoadBalancerOriginModel:
        """Add an origin to an origin group.

        Args:
            lb_id: Load balancer ID.
            group_id: Origin group ID.
            **kwargs: Origin fields.

        Returns:
            Response dict.
        """
        return self._json(
            "POST",
            f"{self.base_url}/loadbalancer/{lb_id}/origingroup/{group_id}/origin",
            json=kwargs,
            expect=LoadBalancerOriginModel,
        )

    def update_origin(
        self,
        lb_id: int,
        group_id: int,
        origin_id: int,
        **kwargs: Unpack[LoadBalancerOriginCreateModel],
    ) -> LoadBalancerOriginModel:
        """Update an origin.

        Args:
            lb_id: Load balancer ID.
            group_id: Origin group ID.
            origin_id: Origin ID.
            **kwargs: Fields to update.

        Returns:
            Response dict.
        """
        return self._json(
            "POST",
            f"{self.base_url}/loadbalancer/{lb_id}/origingroup/{group_id}/origin/{origin_id}",
            json=kwargs,
            expect=LoadBalancerOriginModel,
        )

    def delete_origin(self, lb_id: int, group_id: int, origin_id: int) -> dict:
        """Delete an origin.

        Args:
            lb_id: Load balancer ID.
            group_id: Origin group ID.
            origin_id: Origin ID.

        Returns:
            Response dict.
        """
        return self._json(
            "DELETE",
            f"{self.base_url}/loadbalancer/{lb_id}/origingroup/{group_id}/origin/{origin_id}",
        )

    def get_load_balancer_statistics(self, id: int, **kwargs: Any) -> LoadBalancerStatisticsModel:
        """Get statistics for a load balancer.

        Args:
            id: Load balancer ID.
            **kwargs: Query params (from, to, hourly, exactRange).

        Returns:
            Response dict.
        """
        return self._json(
            "GET",
            f"{self.base_url}/loadbalancer/{id}/statistics",
            params=kwargs,
            expect=LoadBalancerStatisticsModel,
        )

    def get_load_balancer_pull_zones(
        self, id: int, **kwargs: Any
    ) -> LoadBalancerStatisticsEndpointGetAttachedPullZonesResponse:
        """Get pull zones using a load balancer.

        Args:
            id: Load balancer ID.
            **kwargs: Query params (from, to).

        Returns:
            Response dict.
        """
        return self._json(
            "GET",
            f"{self.base_url}/loadbalancer/{id}/pullzones",
            params=kwargs,
            expect=LoadBalancerStatisticsEndpointGetAttachedPullZonesResponse,
        )

    def get_load_balancer_account_statistics(
        self, **kwargs: Any
    ) -> LoadBalancerStatisticsEndpointGetLoadBalancerAccountStatisticsResponse:
        """Get account-wide load balancer statistics.

        Args:
            **kwargs: Query params (from, to).

        Returns:
            Response dict.
        """
        return self._json(
            "GET",
            f"{self.base_url}/loadbalancer/statistics",
            params=kwargs,
            expect=LoadBalancerStatisticsEndpointGetLoadBalancerAccountStatisticsResponse,
        )

    def get_load_balancer_usage(self, id: int, **kwargs: Any) -> LoadBalancerUsageModel:
        """Get usage for a load balancer.

        Args:
            id: Load balancer ID.
            **kwargs: Query params (year, month).

        Returns:
            Response dict.
        """
        return self._json(
            "GET",
            f"{self.base_url}/loadbalancer/{id}/usage",
            params=kwargs,
            expect=LoadBalancerUsageModel,
        )
