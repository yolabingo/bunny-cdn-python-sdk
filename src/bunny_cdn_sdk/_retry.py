"""Retry transport for httpx — exponential backoff with jitter (internal)."""

from __future__ import annotations

import random
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

_STATUS_TOO_MANY_REQUESTS = 429
_STATUS_SERVER_ERROR_MIN = 500
_STATUS_SERVER_ERROR_MAX = 600


def _parse_retry_after(value: str) -> float:
    """Parse a Retry-After header value and return delay in seconds (>= 0.0).

    Supports two RFC 7231 formats:
    - Integer seconds: ``Retry-After: 60``
    - HTTP-date:       ``Retry-After: Wed, 21 Oct 2015 07:28:00 GMT``

    Returns 0.0 if the value cannot be parsed.
    """
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_date = parsedate_to_datetime(value)
            delta = (retry_date - datetime.now(UTC)).total_seconds()
            return max(0.0, delta)
        except Exception:  # noqa: BLE001
            return 0.0


class RetryTransport(httpx.BaseTransport):
    """Composable httpx transport that adds retry logic to any inner transport.

    Wraps an existing ``httpx.BaseTransport`` and retries failed requests
    using exponential backoff with full jitter.

    Retry triggers:
    - HTTP 429 — respects ``Retry-After`` header when present
    - HTTP 5xx — any server error response
    - ``httpx.ConnectError`` — network connection failure
    - ``httpx.TimeoutException`` — request or connect timeout

    Usage::

        import httpx
        from bunny_cdn_sdk import RetryTransport, CoreClient

        inner = httpx.HTTPTransport()
        retry_transport = RetryTransport(inner, max_retries=3, backoff_base=0.5)
        client = httpx.Client(transport=retry_transport)
        core = CoreClient(api_key="...", client=client)
    """

    def __init__(
        self,
        inner: httpx.BaseTransport,
        *,
        max_retries: int = 3,
        backoff_base: float = 0.5,
    ) -> None:
        """Initialise the retry transport.

        Args:
            inner: The underlying transport to delegate requests to.
            max_retries: Maximum number of retries (not counting the initial attempt).
                         ``max_retries=3`` means up to 4 total calls.
            backoff_base: Base delay in seconds for exponential backoff.
                          Delay for attempt N is ``uniform(0, min(60, base * 2**N))``.
        """
        self._inner = inner
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    def handle_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        """Handle a single request, retrying on retriable failures.

        On the final attempt (attempt == max_retries), returns the failed response
        for status-code errors (so ``_BaseClient._request`` can call
        ``raise_for_status()`` and map it to the correct SDK exception). For network
        exceptions on the final attempt, re-raises the exception directly.

        Args:
            request: The outbound httpx.Request to execute.

        Returns:
            The httpx.Response from the inner transport (possibly a non-2xx response
            on final attempt if all retries are exhausted for a status-code trigger).

        Raises:
            httpx.ConnectError: If all attempts fail with a connection error.
            httpx.TimeoutException: If all attempts fail with a timeout.
        """
        # Initialize response before loop to satisfy ty's possibly-unresolved-reference rule.
        response: httpx.Response = httpx.Response(0)

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                delay = self._backoff_delay(attempt - 1, response)
                time.sleep(delay)
            try:
                response = self._inner.handle_request(request)
                if self._should_retry_response(response) and attempt < self._max_retries:
                    continue
            except (httpx.ConnectError, httpx.TimeoutException):
                if attempt >= self._max_retries:
                    raise
            else:
                return response
        # Unreachable: the loop always returns or raises before reaching here.
        return response  # type: ignore[return-value]  # pragma: no cover

    def close(self) -> None:
        """Close the inner transport and release its resources."""
        self._inner.close()

    def _should_retry_response(self, response: httpx.Response) -> bool:
        """Return True if the response status code warrants a retry."""
        return (
            response.status_code == _STATUS_TOO_MANY_REQUESTS
            or _STATUS_SERVER_ERROR_MIN <= response.status_code < _STATUS_SERVER_ERROR_MAX
        )

    def _backoff_delay(
        self,
        attempt: int,
        response: httpx.Response | None = None,
    ) -> float:
        """Compute the delay in seconds before the next retry attempt.

        For 429 responses with a ``Retry-After`` header, uses the header value.
        Otherwise applies full-jitter exponential backoff:
        ``uniform(0, min(60.0, backoff_base * 2**attempt))``.

        Args:
            attempt: Zero-indexed retry attempt number (0 = first retry).
            response: The last response received, or None for network exceptions.

        Returns:
            Delay in seconds (>= 0.0).
        """
        if response is not None and response.status_code == _STATUS_TOO_MANY_REQUESTS:
            retry_after = response.headers.get("retry-after")
            if retry_after is not None:
                return _parse_retry_after(retry_after)
        cap = 60.0
        return random.uniform(0, min(cap, self._backoff_base * (2**attempt)))  # noqa: S311
