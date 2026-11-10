"""Partner Portal API client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bunny_cdn_sdk._client import _BaseClient

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx2

__all__ = ["PartnerClient"]

_BASE_URL = "https://api.bunny.net/partner"


class PartnerClient(_BaseClient):
    """Bunny Partner Portal API client.

    Wraps the Partner API: customers, invitations, overviews, audit logs, contract,
    billing and invoices, pricing, and per-customer product access. Responses are
    returned as the raw JSON Bunny sends. Request and response fields are PascalCase,
    as in the Bunny spec.

    Args:
        api_key: Partner API key: the API key of your bunny.net partner account, not a
            customer's account API key.
        base_url: Base URL for the Partner API (default: https://api.bunny.net/partner).
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

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------

    def list_customers(self) -> list:
        """List the partner's customers.

        Returns:
            Response JSON.
        """
        return self._json("GET", f"{self.base_url}/customers")

    def create_customer(self, email: str, **kwargs: Any) -> dict:
        """Create a customer account.

        Args:
            email: Primary account email of the customer (sent as ``Email``).
            **kwargs: Optional body fields, using the spec's names (``FirstName``,
                ``LastName``, ``Country``, ``BillingEmail``, ``CompanyName``,
                ``CompanyVatNumber``, ``InternalNotes``).

        Returns:
            Response JSON.
        """
        return self._json("POST", f"{self.base_url}/customers", json={"Email": email, **kwargs})

    def invite_customer(self, email: str) -> dict:
        """Invite an existing or new user to become a customer.

        Args:
            email: Email address to invite (sent as ``Email``).

        Returns:
            Response JSON.
        """
        return self._json("POST", f"{self.base_url}/customers/invite", json={"Email": email})

    def get_customer_overview(self, customer_user_id: str) -> dict:
        """Get a customer overview.

        Args:
            customer_user_id: Customer user ID.

        Returns:
            Response JSON.
        """
        return self._json("GET", f"{self.base_url}/customer/{customer_user_id}")

    def get_partner_overview(self) -> dict:
        """Get the partner overview.

        Returns:
            Response JSON.
        """
        return self._json("GET", f"{self.base_url}/overview")

    def iter_audit_log(  # noqa: PLR0913
        self,
        customer_user_id: str,
        date: str,
        *,
        product: list[str] | None = None,
        resource_type: list[str] | None = None,
        resource_id: list[str] | None = None,
        actor_id: list[str] | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> Iterator[dict]:
        """Iterate over all of a customer's audit log entries for a date.

        Follows ``ContinuationToken`` while ``HasMoreData`` is true; stops on an empty
        token or an empty ``Logs`` page. Arguments are those of ``get_audit_log``
        (``limit`` is the page size).

        Yields:
            Entry dicts from each response's ``Logs``.
        """
        token: str | None = None
        while True:
            page = self.get_audit_log(
                customer_user_id,
                date,
                product=product,
                resource_type=resource_type,
                resource_id=resource_id,
                actor_id=actor_id,
                order=order,
                continuation_token=token,
                limit=limit,
            )
            logs = page.get("Logs") or []
            yield from logs
            token = page.get("ContinuationToken")
            if not (logs and token and page.get("HasMoreData")):
                return

    def get_audit_log(  # noqa: PLR0913
        self,
        customer_user_id: str,
        date: str,
        *,
        product: list[str] | None = None,
        resource_type: list[str] | None = None,
        resource_id: list[str] | None = None,
        actor_id: list[str] | None = None,
        order: str | None = None,
        continuation_token: str | None = None,
        limit: int | None = None,
    ) -> dict:
        """Get a customer's audit log for a date.

        Args:
            customer_user_id: Customer user ID.
            date: Date (ISO 8601 date-time string, e.g. ``"2026-01-31"``).
            product: Filter by products.
            resource_type: Filter by resource types.
            resource_id: Filter by resource IDs.
            actor_id: Filter by actor IDs.
            order: ``"Ascending"`` or ``"Descending"``.
            continuation_token: Token from a previous response to fetch the next page.
            limit: Maximum number of entries.

        Returns:
            Response JSON.
        """
        candidates = {
            "Product": product,
            "ResourceType": resource_type,
            "ResourceId": resource_id,
            "ActorId": actor_id,
            "Order": order,
            "ContinuationToken": continuation_token,
            "Limit": limit,
        }
        params = {k: v for k, v in candidates.items() if v is not None}
        return self._json(
            "GET", f"{self.base_url}/customer/{customer_user_id}/audit/{date}", params=params
        )

    # ------------------------------------------------------------------
    # Contract, Billing, Pricing
    # ------------------------------------------------------------------

    def get_contract(self) -> dict:
        """Get the partner contract.

        Returns:
            Response JSON.
        """
        return self._json("GET", f"{self.base_url}/contract")

    def get_customer_billing(self, customer_user_id: str) -> dict:
        """Get a customer's billing records.

        Args:
            customer_user_id: Customer user ID.

        Returns:
            Response JSON.
        """
        return self._json("GET", f"{self.base_url}/customer/{customer_user_id}/billing")

    def download_invoice_pdf(self, customer_user_id: str, billing_record_id: int) -> bytes:
        """Download a customer's invoice as a PDF.

        Args:
            customer_user_id: Customer user ID.
            billing_record_id: Billing record ID.

        Returns:
            Raw PDF bytes.
        """
        url = f"{self.base_url}/customer/{customer_user_id}/billing/{billing_record_id}/pdf"
        return self._request("GET", url).content

    def get_customer_pricing(self, customer_user_id: str) -> dict:
        """Get a customer's pricing.

        Args:
            customer_user_id: Customer user ID.

        Returns:
            Response JSON.
        """
        return self._json("GET", f"{self.base_url}/customer/{customer_user_id}/pricing")

    def get_partner_pricing(self) -> dict:
        """Get the partner pricing.

        Returns:
            Response JSON.
        """
        return self._json("GET", f"{self.base_url}/pricing")

    # ------------------------------------------------------------------
    # Customer products
    # ------------------------------------------------------------------

    def list_customer_products(self, customer_user_id: str) -> list:
        """List the products and whether each is enabled for a customer.

        Args:
            customer_user_id: Customer user ID.

        Returns:
            Response JSON.
        """
        return self._json("GET", f"{self.base_url}/customer/{customer_user_id}/products")

    def set_customer_product(
        self, customer_user_id: str, product_id: int, *, enabled: bool | None = None
    ) -> None:
        """Enable or disable a product for a customer.

        Args:
            customer_user_id: Customer user ID.
            product_id: 1 CDN, 2 Database, 3 DNS, 4 Magic Containers, 5 Optimizer,
                6 Edge Scripting, 7 Shield, 8 Storage, 9 Stream.
            enabled: Whether the product is enabled; omitted from the request when None.
        """
        params = {} if enabled is None else {"enabled": enabled}
        self._request(
            "PUT",
            f"{self.base_url}/customer/{customer_user_id}/products/{product_id}",
            params=params,
        )
