"""Base HTTP client (internal)."""

from __future__ import annotations

import importlib.metadata
import warnings
from typing import Any, Never, Self

import httpx2

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

_USER_AGENT = f"bunny-cdn-sdk/{importlib.metadata.version('bunny-cdn-sdk')}"

# HTTP status code constants (PLR2004)
_HTTP_UNAUTHORIZED = 401
_HTTP_NOT_FOUND = 404
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_SERVER_ERROR_MIN = 500
_HTTP_SERVER_ERROR_MAX = 600


def _extract_error_message(response: httpx2.Response, status_code: int) -> str:
    """Extract a human-readable error message from an HTTP error response."""
    try:
        body = response.json()
    except ValueError:
        body = None
    message = body.get("Message") if isinstance(body, dict) else None
    return message or response.text or f"HTTP {status_code}"


def _raise_for_status_code(
    status_code: int,
    message: str,
    response: httpx2.Response,
    exc: httpx2.HTTPStatusError,
) -> Never:
    """Raise the appropriate Bunny exception for an HTTP error status code."""
    if status_code == _HTTP_UNAUTHORIZED:
        raise BunnyAuthenticationError(status_code, message, response) from exc
    if status_code == _HTTP_NOT_FOUND:
        raise BunnyNotFoundError(status_code, message, response) from exc
    if status_code == _HTTP_TOO_MANY_REQUESTS:
        raise BunnyRateLimitError(status_code, message, response) from exc
    if _HTTP_SERVER_ERROR_MIN <= status_code < _HTTP_SERVER_ERROR_MAX:
        raise BunnyServerError(status_code, message, response) from exc
    raise BunnyAPIError(status_code, message, response) from exc


class _BaseClient:
    """Base HTTP client (internal)."""

    def __init__(
        self,
        api_key: str,
        client: httpx2.Client | None = None,
        *,
        max_retries: int = 0,
        backoff_base: float = 0.5,
    ) -> None:
        """Initialize the base client.

        Args:
            api_key: API key for authentication
            client: Optional httpx2.Client to use; if not provided, one is created
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
                httpx2.HTTPTransport(),
                max_retries=max_retries,
                backoff_base=backoff_base,
            )
            self._client = httpx2.Client(transport=transport)
            self._client_owner = True
        else:
            self._client = httpx2.Client()
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
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client if this SDK client created it."""
        if self._client_owner:
            self._client.close()

    def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx2.Response:
        """Make an HTTP request with auth and error mapping.

        Args:
            method: HTTP method
            url: URL to request
            **kwargs: Additional arguments to pass to httpx2.Client.request

        Returns:
            The httpx2.Response object

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
            response = self._client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
        except httpx2.HTTPStatusError as exc:
            status_code = exc.response.status_code
            message = _extract_error_message(exc.response, status_code)
            _raise_for_status_code(status_code, message, exc.response, exc)
        except httpx2.ConnectError as exc:
            msg = f"Connection error: {exc}"
            raise BunnyConnectionError(msg) from exc
        except httpx2.TimeoutException as exc:
            msg = f"Request timeout: {exc}"
            raise BunnyTimeoutError(msg) from exc
        else:
            return response

    def _json(self, method: str, url: str, **kwargs: Any) -> Any:
        """Make a request and return the parsed JSON body, or {} for an empty body."""
        response = self._request(method, url, **kwargs)
        return response.json() if response.content else {}
