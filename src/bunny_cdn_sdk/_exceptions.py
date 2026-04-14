"""Exception hierarchy for bunny-cdn-sdk."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

__all__ = [
    "BunnyAPIError",
    "BunnyAuthenticationError",
    "BunnyConnectionError",
    "BunnyNotFoundError",
    "BunnyRateLimitError",
    "BunnySDKError",
    "BunnyServerError",
    "BunnyTimeoutError",
]


class BunnySDKError(Exception):
    """Base class for all bunny-cdn-sdk errors."""


class BunnyAPIError(BunnySDKError):
    """Raised when the Bunny CDN API returns an HTTP error response."""

    def __init__(
        self,
        status_code: int,
        message: str,
        response: httpx.Response,
    ) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.response = response

    def __str__(self) -> str:
        return f"HTTP {self.status_code}: {self.message}"


class BunnyAuthenticationError(BunnyAPIError):
    """Raised on HTTP 401 Unauthorized responses."""


class BunnyNotFoundError(BunnyAPIError):
    """Raised on HTTP 404 Not Found responses."""


class BunnyRateLimitError(BunnyAPIError):
    """Raised on HTTP 429 Too Many Requests responses."""


class BunnyServerError(BunnyAPIError):
    """Raised on HTTP 5xx Server Error responses."""


class BunnyConnectionError(BunnySDKError):
    """Raised when a network-level connection failure occurs (not an HTTP response)."""


class BunnyTimeoutError(BunnyConnectionError):
    """Raised when a request times out before receiving a response."""
