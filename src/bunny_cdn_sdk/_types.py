"""TypedDict definitions for API response envelopes."""

from __future__ import annotations

from typing import TypedDict

__all__ = ["PaginatedResponse"]


class PaginatedResponse(TypedDict):
    """Response envelope for paginated Core API endpoints."""

    Items: list
    CurrentPage: int
    TotalItems: int
    HasMoreItems: bool
