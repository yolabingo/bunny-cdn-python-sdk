"""Pagination helpers (populated in Phase 2)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, AsyncIterator, Awaitable

from bunny_cdn_sdk._types import PaginatedResponse

__all__ = ["pagination_iterator", "list_single_page"]


async def pagination_iterator(
    fetch_page: Callable[[int], Awaitable[PaginatedResponse]], start_page: int = 1
) -> AsyncIterator[Any]:
    """
    Async generator that yields individual items from paginated API responses.

    Handles automatic pagination by checking HasMoreItems and fetching subsequent pages.
    Each item from the Items array is yielded individually.

    Args:
        fetch_page: Async callable that takes a page number and returns a PaginatedResponse dict
        start_page: Starting page number (default 1)

    Yields:
        Individual items from the Items array of each page
    """
    current_page = start_page
    while True:
        response = await fetch_page(current_page)
        for item in response["Items"]:
            yield item
        if not response["HasMoreItems"]:
            break
        current_page += 1


async def list_single_page(
    fetch_page: Callable[[int], Awaitable[PaginatedResponse]], page: int = 1
) -> PaginatedResponse:
    """
    Fetches a single page of results without automatic pagination.

    Returns the raw response dict from the API endpoint.

    Args:
        fetch_page: Async callable that takes a page number and returns a PaginatedResponse dict
        page: Page number to fetch (default 1)

    Returns:
        PaginatedResponse dict containing Items, CurrentPage, TotalItems, HasMoreItems
    """
    return await fetch_page(page)
