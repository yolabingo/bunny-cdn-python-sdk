"""Bunny CDN Storage API client."""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any, BinaryIO

from bunny_cdn_sdk._client import _BaseClient

if TYPE_CHECKING:
    import builtins

    import httpx2

__all__ = ["StorageClient"]

# Hard-coded 10-region mapping per STOR-05
REGION_MAP: dict[str, str] = {
    "falkenstein": "https://storage.bunnycdn.com",
    "de": "https://de.storage.bunnycdn.com",
    "ny": "https://ny.storage.bunnycdn.com",
    "la": "https://la.storage.bunnycdn.com",
    "sg": "https://sg.storage.bunnycdn.com",
    "syd": "https://syd.storage.bunnycdn.com",
    "uk": "https://uk.storage.bunnycdn.com",
    "se": "https://se.storage.bunnycdn.com",
    "br": "https://br.storage.bunnycdn.com",
    "jh": "https://jh.storage.bunnycdn.com",
}


class StorageClient(_BaseClient):
    """Bunny CDN Storage API client.

    Provides upload, download, delete, and list operations against a single
    Bunny Storage Zone. Requests are authenticated with the zone password in the
    ``AccessKey`` header.

    Args:
        zone_name: Name of the Bunny Storage Zone.
        password: Storage Zone password, sent as the ``AccessKey`` header.
        region: Storage region key.  Must be one of the 10 supported regions
            (default: ``"falkenstein"``).  See ``REGION_MAP`` for the full list.
        client: Optional ``httpx2.Client`` to inject (keyword-only, advanced use).
            When provided, max_retries is ignored.
        max_retries: Number of retry attempts on 429/5xx/network errors (default 0 = no retry).
        backoff_base: Base delay in seconds for exponential backoff (default 0.5).

    Raises:
        ValueError: If ``region`` is not a recognized key in ``REGION_MAP``.
    """

    def __init__(
        self,
        zone_name: str,
        password: str,
        region: str = "falkenstein",
        *,
        client: httpx2.Client | None = None,
        max_retries: int = 0,
        backoff_base: float = 0.5,
    ) -> None:
        if region not in REGION_MAP:
            msg = f"Unknown region {region!r}. Valid regions: {', '.join(sorted(REGION_MAP))}"
            raise ValueError(msg)
        super().__init__(
            password, client=client, max_retries=max_retries, backoff_base=backoff_base
        )
        self.zone_name = zone_name
        self.region = region
        self.base_url: str = REGION_MAP[region]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        """Build the full Storage API URL for ``path``.

        Path is joined under ``{base_url}/{zone_name}/``.  A leading slash on
        ``path`` is stripped to avoid a double-slash in the resulting URL.

        Args:
            path: Relative file or directory path within the zone.

        Returns:
            Full HTTPS URL string.
        """
        clean_path = urllib.parse.quote(path.lstrip("/"), safe="/")
        return f"{self.base_url}/{self.zone_name}/{clean_path}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload(
        self,
        path: str,
        data: bytes | BinaryIO,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Upload a file to the storage zone (STOR-01).

        Args:
            path: Destination path within the zone (e.g. ``"photos/image.jpg"``).
            data: File content as ``bytes`` or a file-like object opened in
                binary mode.  File-like objects are streamed by httpx2 without
                buffering the entire file in memory (T-03-09 mitigation).
            content_type: Optional MIME type for the ``Content-Type`` header.
                If omitted, httpx2 defaults to ``application/octet-stream``.

        Returns:
            Parsed JSON response body as a plain ``dict`` (may be empty on 204).
        """
        url = self._build_url(path)
        headers = {"Content-Type": content_type} if content_type is not None else {}
        return self._json("PUT", url, headers=headers, content=data)

    def download(self, path: str) -> bytes:
        """Download a file from the storage zone (STOR-02).

        Args:
            path: Source path within the zone (e.g. ``"photos/image.jpg"``).

        Returns:
            Raw file bytes.
        """
        url = self._build_url(path)
        return self._request("GET", url).content

    def delete(self, path: str) -> None:
        """Delete a file from the storage zone (STOR-03).

        Args:
            path: Path of the file to delete (e.g. ``"photos/image.jpg"``).
        """
        url = self._build_url(path)
        self._request("DELETE", url)

    def list(self, path: str = "/") -> builtins.list[dict[str, Any]]:
        """List files and directories in the storage zone (STOR-04).

        The path should end with ``"/"`` to indicate a directory listing.
        Listing ``"/"`` returns top-level contents of the zone.

        Args:
            path: Directory path to list (default: ``"/"`` for zone root).

        Returns:
            List of file/directory metadata dicts returned by the Storage API.
        """
        url = self._build_url(path)
        return self._json("GET", url)
