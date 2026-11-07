"""Shield (WAF) API client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bunny_cdn_sdk._client import _BaseClient

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx2

__all__ = ["ShieldClient"]

_BASE_URL = "https://api.bunny.net/shield"


class ShieldClient(_BaseClient):
    """Bunny Shield (WAF) API client.

    Wraps the core Shield API: shield zones, WAF rules, custom WAF rules, rate limits,
    access lists, bot detection, event logs and metrics. Responses are returned as the
    raw JSON Bunny sends; the ``{data, page, error}`` envelope is not unwrapped except
    by the ``iter_*`` helpers.

    Args:
        api_key: Bunny CDN account API key.
        base_url: Base URL for the Shield API (default: https://api.bunny.net/shield).
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

    def _iter_pages(self, path: str, per_page: int) -> Iterator[dict]:
        """Yield every ``data`` item from a Shield ``{data, page: {nextPage}}`` list endpoint."""
        page = 1
        while True:
            resp = self._json(
                "GET", f"{self.base_url}{path}", params={"page": page, "perPage": per_page}
            )
            data = resp.get("data") or []
            yield from data
            if not data or not (resp.get("page") or {}).get("nextPage"):
                return
            page += 1

    # ------------------------------------------------------------------
    # Shield Zones
    # ------------------------------------------------------------------

    def list_shield_zones(self, page: int = 1, per_page: int = 10) -> dict:
        """List shield zones (one page).

        Args:
            page: Page number (1-based).
            per_page: Items per page.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "GET", f"{self.base_url}/shield-zones", params={"page": page, "perPage": per_page}
        )

    def iter_shield_zones(self, per_page: int = 100) -> Iterator[dict]:
        """Iterate over all shield zones across pages.

        Args:
            per_page: Items per page.

        Yields:
            Item dicts from each page's ``data`` list.
        """
        yield from self._iter_pages("/shield-zones", per_page)

    def get_shield_zone(self, id: int) -> dict:
        """Get a shield zone by ID.

        Args:
            id: Shield zone ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/shield-zone/{id}")

    def get_shield_zone_by_pull_zone(self, pull_zone_id: int) -> dict:
        """Get the shield zone attached to a pull zone.

        Args:
            pull_zone_id: Pull zone ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/shield-zone/get-by-pullzone/{pull_zone_id}")

    def create_shield_zone(self, pull_zone_id: int, **shield_zone: Any) -> dict:
        """Create a shield zone for a pull zone.

        Args:
            pull_zone_id: Pull zone ID to protect.
            **shield_zone: Shield zone settings, sent as the ``shieldZone`` object.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "POST",
            f"{self.base_url}/shield-zone",
            json={"pullZoneId": pull_zone_id, "shieldZone": shield_zone},
        )

    def update_shield_zone(self, shield_zone_id: int, **shield_zone: Any) -> dict:
        """Update a shield zone (``PATCH /shield-zone``; the ID travels in the body).

        Args:
            shield_zone_id: Shield zone ID.
            **shield_zone: Shield zone settings to change.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "PATCH",
            f"{self.base_url}/shield-zone",
            json={
                "shieldZoneId": shield_zone_id,
                "shieldZone": {"shieldZoneId": shield_zone_id, **shield_zone},
            },
        )

    # ------------------------------------------------------------------
    # WAF Rules
    # ------------------------------------------------------------------

    def list_waf_rules(self, zone_id: int) -> dict:
        """List the managed WAF rules for a shield zone.

        Args:
            zone_id: Shield zone ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/waf/rules/{zone_id}")

    def list_custom_waf_rules(self, zone_id: int, page: int = 1, per_page: int = 10) -> dict:
        """List custom WAF rules (one page).

        Args:
            zone_id: Shield zone ID.
            page: Page number (1-based).
            per_page: Items per page.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "GET",
            f"{self.base_url}/waf/custom-rules/{zone_id}",
            params={"page": page, "perPage": per_page},
        )

    def iter_custom_waf_rules(self, zone_id: int, per_page: int = 100) -> Iterator[dict]:
        """Iterate over all custom WAF rules across pages.

        Args:
            zone_id: Shield zone ID.
            per_page: Items per page.

        Yields:
            Item dicts from each page's ``data`` list.
        """
        yield from self._iter_pages(f"/waf/custom-rules/{zone_id}", per_page)

    def get_custom_waf_rule(self, id: int) -> dict:
        """Get a custom WAF rule.

        Args:
            id: Custom WAF rule ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/waf/custom-rule/{id}")

    def create_custom_waf_rule(self, shield_zone_id: int, **kwargs: Any) -> dict:
        """Create a custom WAF rule.

        Args:
            shield_zone_id: Shield zone ID.
            **kwargs: Rule fields (ruleName, ruleDescription, ruleConfiguration).

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "POST",
            f"{self.base_url}/waf/custom-rule",
            json={"shieldZoneId": shield_zone_id, **kwargs},
        )

    def update_custom_waf_rule(self, id: int, **kwargs: Any) -> dict:
        """Update a custom WAF rule (PATCH).

        Args:
            id: Custom WAF rule ID.
            **kwargs: Fields to change.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("PATCH", f"{self.base_url}/waf/custom-rule/{id}", json=kwargs)

    def delete_custom_waf_rule(self, id: int) -> dict:
        """Delete a custom WAF rule.

        Args:
            id: Custom WAF rule ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("DELETE", f"{self.base_url}/waf/custom-rule/{id}")

    def list_waf_profiles(self) -> dict:
        """List WAF profiles.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/waf/profiles")

    def get_waf_enums(self) -> dict:
        """Get WAF enum values.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/waf/enums")

    def get_waf_engine_config(self) -> dict:
        """Get the WAF engine configuration.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/waf/engine-config")

    def list_triggered_waf_rules(self, zone_id: int) -> dict:
        """List triggered WAF rules awaiting review.

        Args:
            zone_id: Shield zone ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/waf/rules/review-triggered/{zone_id}")

    def review_triggered_waf_rule(self, zone_id: int, rule_id: str, action: int) -> dict:
        """Review a triggered WAF rule.

        Args:
            zone_id: Shield zone ID.
            rule_id: Triggered rule ID.
            action: 0 = Ignore, 1 = LogOnly, 2 = DisableRule.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "POST",
            f"{self.base_url}/waf/rules/review-triggered/{zone_id}",
            json={"ruleId": rule_id, "action": action},
        )

    # ------------------------------------------------------------------
    # Rate Limits
    # ------------------------------------------------------------------

    def list_rate_limits(self, zone_id: int, page: int = 1, per_page: int = 10) -> dict:
        """List rate limits (one page).

        Args:
            zone_id: Shield zone ID.
            page: Page number (1-based).
            per_page: Items per page.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "GET",
            f"{self.base_url}/rate-limits/{zone_id}",
            params={"page": page, "perPage": per_page},
        )

    def iter_rate_limits(self, zone_id: int, per_page: int = 100) -> Iterator[dict]:
        """Iterate over all rate limits across pages.

        Args:
            zone_id: Shield zone ID.
            per_page: Items per page.

        Yields:
            Item dicts from each page's ``data`` list.
        """
        yield from self._iter_pages(f"/rate-limits/{zone_id}", per_page)

    def get_rate_limit(self, id: int) -> dict:
        """Get a rate limit.

        Args:
            id: Rate limit ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/rate-limit/{id}")

    def create_rate_limit(self, shield_zone_id: int, **kwargs: Any) -> dict:
        """Create a rate limit.

        Args:
            shield_zone_id: Shield zone ID.
            **kwargs: Rule fields (ruleName, ruleDescription, ruleConfiguration).

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "POST", f"{self.base_url}/rate-limit", json={"shieldZoneId": shield_zone_id, **kwargs}
        )

    def update_rate_limit(self, id: int, **kwargs: Any) -> dict:
        """Update a rate limit (PATCH).

        Args:
            id: Rate limit ID.
            **kwargs: Fields to change.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("PATCH", f"{self.base_url}/rate-limit/{id}", json=kwargs)

    def delete_rate_limit(self, id: int) -> dict:
        """Delete a rate limit.

        Args:
            id: Rate limit ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("DELETE", f"{self.base_url}/rate-limit/{id}")

    # ------------------------------------------------------------------
    # Access Lists
    # ------------------------------------------------------------------

    def list_access_lists(self, zone_id: int) -> dict:
        """List access lists for a shield zone.

        Args:
            zone_id: Shield zone ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/shield-zone/{zone_id}/access-lists")

    def get_access_list(self, zone_id: int, id: int) -> dict:
        """Get an access list.

        Args:
            zone_id: Shield zone ID.
            id: Access list ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/shield-zone/{zone_id}/access-lists/{id}")

    def create_access_list(self, zone_id: int, **kwargs: Any) -> dict:
        """Create a custom access list.

        Args:
            zone_id: Shield zone ID.
            **kwargs: Fields: name, type, content (required), description, checksum.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "POST", f"{self.base_url}/shield-zone/{zone_id}/access-lists", json=kwargs
        )

    def update_access_list(self, zone_id: int, id: int, **kwargs: Any) -> dict:
        """Update a custom access list (PATCH).

        Args:
            zone_id: Shield zone ID.
            id: Access list ID.
            **kwargs: Fields to change (name, content, checksum).

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "PATCH", f"{self.base_url}/shield-zone/{zone_id}/access-lists/{id}", json=kwargs
        )

    def update_access_list_configuration(self, zone_id: int, id: int, **kwargs: Any) -> dict:
        """Update an access list's enabled state or action (PATCH).

        Args:
            zone_id: Shield zone ID.
            id: Access list ID.
            **kwargs: Fields to change (isEnabled, action).

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "PATCH",
            f"{self.base_url}/shield-zone/{zone_id}/access-lists/configurations/{id}",
            json=kwargs,
        )

    def delete_access_list(self, zone_id: int, id: int) -> dict:
        """Delete a custom access list.

        Args:
            zone_id: Shield zone ID.
            id: Access list ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("DELETE", f"{self.base_url}/shield-zone/{zone_id}/access-lists/{id}")

    # ------------------------------------------------------------------
    # Bot Detection
    # ------------------------------------------------------------------

    def get_bot_detection(self, zone_id: int) -> dict:
        """Get bot detection settings.

        Args:
            zone_id: Shield zone ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/shield-zone/{zone_id}/bot-detection")

    def update_bot_detection(self, zone_id: int, **kwargs: Any) -> dict:
        """Update bot detection settings (PATCH; ``shieldZoneId`` is added to the body).

        Args:
            zone_id: Shield zone ID.
            **kwargs: Fields to change (executionMode, requestIntegrity,
                ipAddress, browserFingerprint).

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "PATCH",
            f"{self.base_url}/shield-zone/{zone_id}/bot-detection",
            json={"shieldZoneId": zone_id, **kwargs},
        )

    # ------------------------------------------------------------------
    # Event Logs
    # ------------------------------------------------------------------

    def get_event_logs(self, zone_id: int, date: str, continuation_token: str) -> dict:
        """Get event logs for one day.

        Args:
            zone_id: Shield zone ID.
            date: Day to fetch, formatted ``MM-dd-yyyy``.
            continuation_token: Required path segment. The spec does not document the value
            to use for the first page; pass the token from the previous response for later pages.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json(
            "GET", f"{self.base_url}/event-logs/{zone_id}/{date}/{continuation_token}"
        )

    def search_event_logs(self, zone_id: int, **kwargs: Any) -> dict:
        """Search event logs.

        Args:
            zone_id: Shield zone ID.
            **kwargs: Search body (from, to, query, filters, groupBy, buckets, page, pageSize).
            The spec does not document the units of ``from``/``to`` (seconds vs
            milliseconds); they are passed through unchanged. ``from`` is a Python
            keyword, so pass it as ``**{"from": ...}``.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("POST", f"{self.base_url}/event-logs/{zone_id}/search", json=kwargs)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics_overview(self, zone_id: int) -> dict:
        """Get the metrics overview for a shield zone.

        Args:
            zone_id: Shield zone ID.

        Returns:
            Response JSON (envelope not unwrapped).
        """
        return self._json("GET", f"{self.base_url}/metrics/overview/{zone_id}")
