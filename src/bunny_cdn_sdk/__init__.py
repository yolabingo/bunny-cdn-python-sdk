"""Bunny CDN Python SDK.

A thin, typed Python SDK wrapping Bunny CDN REST APIs.
"""

import importlib.metadata

__version__ = importlib.metadata.version("bunny-cdn-sdk")

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
from bunny_cdn_sdk._retry import RetryTransport
from bunny_cdn_sdk.core import CoreClient
from bunny_cdn_sdk.logs import LoggingClient
from bunny_cdn_sdk.partner import PartnerClient
from bunny_cdn_sdk.shield import ShieldClient
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
    "LoggingClient",
    "PartnerClient",
    "RetryTransport",
    "ShieldClient",
    "StorageClient",
    "__version__",
]
