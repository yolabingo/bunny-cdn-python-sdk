"""Base HTTP client (internal)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Self

import httpx

from bunny_cdn_sdk._exceptions import (
    BunnyAPIError,
    BunnyAuthenticationError,
    BunnyConnectionError,
    BunnyNotFoundError,
    BunnyRateLimitError,
    BunnyServerError,
    BunnyTimeoutError,
)

if TYPE_CHECKING:
    from typing import Awaitable


class _BaseClient:
    """Base HTTP client (internal)."""

    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the base client.

        Args:
            api_key: API key for authentication
            client: Optional httpx.AsyncClient to use; if not provided, one is created
        """
        self.api_key = api_key
        if client is not None:
            self._client = client
            self._client_owner = False
        else:
            self._client = httpx.AsyncClient()
            self._client_owner = True

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        if self._client_owner:
            await self._client.aclose()

    def __enter__(self) -> Self:
        """Sync context manager entry."""
        asyncio.run(self.__aenter__())
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Sync context manager exit."""
        asyncio.run(self.__aexit__(exc_type, exc_val, exc_tb))

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an HTTP request with auth and error mapping.

        Args:
            method: HTTP method
            url: URL to request
            **kwargs: Additional arguments to pass to httpx.AsyncClient.request

        Returns:
            The httpx.Response object

        Raises:
            BunnyAuthenticationError: On HTTP 401
            BunnyNotFoundError: On HTTP 404
            BunnyRateLimitError: On HTTP 429
            BunnyServerError: On HTTP 5xx
            BunnyAPIError: On other HTTP errors
            BunnyConnectionError: On network connection errors
            BunnyTimeoutError: On request timeouts
        """
        # Inject headers — pop from kwargs to avoid duplicate keyword argument
        headers = {**kwargs.pop("headers", {})}
        headers["AccessKey"] = self.api_key
        headers["User-Agent"] = "bunny-cdn-sdk/0.1.0"

        try:
            response = await self._client.request(
                method,
                url,
                headers=headers,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            # Map HTTP errors to exception subclasses
            status_code = exc.response.status_code
            response = exc.response

            # Try to extract error message from response
            try:
                message = response.json().get("Message") or response.text or f"HTTP {status_code}"
            except Exception:
                message = response.text or f"HTTP {status_code}"

            if status_code == 401:
                raise BunnyAuthenticationError(status_code, message, response) from exc
            elif status_code == 404:
                raise BunnyNotFoundError(status_code, message, response) from exc
            elif status_code == 429:
                raise BunnyRateLimitError(status_code, message, response) from exc
            elif 500 <= status_code < 600:
                raise BunnyServerError(status_code, message, response) from exc
            else:
                raise BunnyAPIError(status_code, message, response) from exc
        except httpx.ConnectTimeout as exc:
            raise BunnyTimeoutError(f"Connection timeout: {exc}") from exc
        except httpx.ConnectError as exc:
            raise BunnyConnectionError(f"Connection error: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise BunnyTimeoutError(f"Request timeout: {exc}") from exc

    async def _gather(self, *coroutines: Awaitable[Any]) -> list[Any]:
        """Run multiple coroutines concurrently.

        Args:
            *coroutines: Coroutines to run

        Returns:
            List of results in input order
        """
        return await asyncio.gather(*coroutines)

    def _sync_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an HTTP request synchronously.

        Args:
            method: HTTP method
            url: URL to request
            **kwargs: Additional arguments to pass to _request

        Returns:
            The httpx.Response object
        """
        return asyncio.run(self._request(method, url, **kwargs))
