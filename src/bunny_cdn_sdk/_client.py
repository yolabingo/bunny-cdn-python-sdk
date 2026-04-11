"""Base HTTP client (internal)."""

from __future__ import annotations

import importlib.metadata
import warnings
from typing import Any, Self

import httpx

_USER_AGENT = f"bunny-cdn-sdk/{importlib.metadata.version('bunny-cdn-sdk')}"

from bunny_cdn_sdk._exceptions import (
    BunnyAPIError,
    BunnyAuthenticationError,
    BunnyConnectionError,
    BunnyNotFoundError,
    BunnyRateLimitError,
    BunnyServerError,
    BunnyTimeoutError,
)
from bunny_cdn_sdk._retry import RetryTransport


class _BaseClient:
    """Base HTTP client (internal)."""

    def __init__(
        self,
        api_key: str,
        client: httpx.Client | None = None,
        *,
        max_retries: int = 0,
        backoff_base: float = 0.5,
    ) -> None:
        """Initialize the base client.

        Args:
            api_key: API key for authentication
            client: Optional httpx.Client to use; if not provided, one is created
            max_retries: Number of retry attempts on 429/5xx/network errors (default 0 = no retry).
                Ignored when ``client=`` is provided — configure RetryTransport on your
                Client directly in that case. Reasonable values are 1-5.
            backoff_base: Base delay in seconds for exponential backoff (default 0.5).
                Only used when ``max_retries > 0`` and ``client`` is None.
        """
        self.api_key = api_key
        if client is not None:
            if max_retries > 0:
                warnings.warn(
                    "max_retries is ignored when client= is provided. "
                    "Configure RetryTransport on your Client directly.",
                    UserWarning,
                    stacklevel=2,
                )
            self._client = client
            self._client_owner = False
        elif max_retries > 0:
            transport = RetryTransport(
                httpx.HTTPTransport(),
                max_retries=max_retries,
                backoff_base=backoff_base,
            )
            self._client = httpx.Client(transport=transport)
            self._client_owner = True
        else:
            self._client = httpx.Client()
            self._client_owner = True

    def __enter__(self) -> Self:
        """Sync context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Sync context manager exit."""
        if self._client_owner:
            self._client.close()

    def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an HTTP request with auth and error mapping.

        Args:
            method: HTTP method
            url: URL to request
            **kwargs: Additional arguments to pass to httpx.Client.request

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
        headers["User-Agent"] = _USER_AGENT

        try:
            response = self._client.request(
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
            if status_code == 404:
                raise BunnyNotFoundError(status_code, message, response) from exc
            if status_code == 429:
                raise BunnyRateLimitError(status_code, message, response) from exc
            if 500 <= status_code < 600:
                raise BunnyServerError(status_code, message, response) from exc
            raise BunnyAPIError(status_code, message, response) from exc
        except httpx.ConnectTimeout as exc:
            raise BunnyTimeoutError(f"Connection timeout: {exc}") from exc
        except httpx.ConnectError as exc:
            raise BunnyConnectionError(f"Connection error: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise BunnyTimeoutError(f"Request timeout: {exc}") from exc

    def _sync_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Alias for _request. Kept for internal call-site compatibility."""
        return self._request(method, url, **kwargs)
