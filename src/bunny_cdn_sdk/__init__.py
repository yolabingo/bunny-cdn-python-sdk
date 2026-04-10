"""Bunny CDN Python SDK.

A thin, typed Python SDK wrapping Bunny CDN REST APIs.
"""

from typing import TYPE_CHECKING

from bunny_cdn_sdk._exceptions import (
    BunnyAPIError,
    BunnyAuthenticationError,
    BunnyConnectionError,
    BunnyNotFoundError,
    BunnyRateLimitError,
    BunnySDKError,
    BunnyServerError,
    BunnyTimeoutError,
)

if TYPE_CHECKING:
    from bunny_cdn_sdk.core import CoreClient
    from bunny_cdn_sdk.storage import StorageClient

__all__ = [
    "BunnyAPIError",
    "BunnyAuthenticationError",
    "BunnyConnectionError",
    "BunnyNotFoundError",
    "BunnyRateLimitError",
    "BunnySDKError",
    "BunnyServerError",
    "BunnyTimeoutError",
    "CoreClient",
    "StorageClient",
]
