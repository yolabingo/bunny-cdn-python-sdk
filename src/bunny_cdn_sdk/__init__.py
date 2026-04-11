"""Bunny CDN Python SDK.

A thin, typed Python SDK wrapping Bunny CDN REST APIs.
"""

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
