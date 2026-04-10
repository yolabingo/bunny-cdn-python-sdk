"""Bunny CDN Storage API client."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any, BinaryIO

from bunny_cdn_sdk._client import _BaseClient

if TYPE_CHECKING:
    import httpx

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
    Bunny Storage Zone.  Requests are authenticated via HTTP Basic Auth
    (``Authorization: Basic base64(zone_name:password)``).

    Args:
        zone_name: Name of the Bunny Storage Zone.
        password: Storage Zone password (used as both the ``_BaseClient``
            ``api_key`` and the Basic Auth credential).
        region: Storage region key.  Must be one of the 10 supported regions
            (default: ``"falkenstein"``).  See ``REGION_MAP`` for the full list.
        client: Optional ``httpx.AsyncClient`` to reuse; a new one is created if
            not provided.

    Raises:
        ValueError: If ``region`` is not a recognized key in ``REGION_MAP``.
    """

    def __init__(
        self,
        zone_name: str,
        password: str,
        region: str = "falkenstein",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if region not in REGION_MAP:
            raise ValueError(
                f"Unknown region {region!r}. "
                f"Valid regions: {', '.join(sorted(REGION_MAP))}"
            )
        # Pass password as api_key — _BaseClient injects it as AccessKey header.
        # We additionally set Authorization: Basic on every request so the
        # Storage API can validate zone ownership (T-03-07 mitigation).
        super().__init__(password, client)
        self.zone_name = zone_name
        self.password = password
        self.region = region
        self.base_url: str = REGION_MAP[region]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_auth_header(self) -> dict[str, str]:
        """Build the ``Authorization: Basic`` header for this zone.

        Encodes ``zone_name:password`` in base64 per RFC 7617.

        Returns:
            Dict with the ``Authorization`` key set to the encoded credential.
        """
        encoded = base64.b64encode(
            f"{self.zone_name}:{self.password}".encode()
        ).decode()
        return {"Authorization": f"Basic {encoded}"}

    def _build_url(self, path: str) -> str:
        """Build the full Storage API URL for ``path``.

        Path is joined under ``{base_url}/{zone_name}/``.  A leading slash on
        ``path`` is stripped to avoid a double-slash in the resulting URL.

        Args:
            path: Relative file or directory path within the zone.

        Returns:
            Full HTTPS URL string.
        """
        clean_path = path.lstrip("/")
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
                binary mode.  File-like objects are streamed by httpx without
                buffering the entire file in memory (T-03-09 mitigation).
            content_type: Optional MIME type for the ``Content-Type`` header.
                If omitted, httpx defaults to ``application/octet-stream``.

        Returns:
            Parsed JSON response body as a plain ``dict`` (may be empty on 204).
        """
        url = self._build_url(path)
        headers = self._build_auth_header()
        if content_type is not None:
            headers["Content-Type"] = content_type
        response = self._sync_request("PUT", url, headers=headers, content=data)
        return response.json() if response.content else {}

    def download(self, path: str) -> bytes:
        """Download a file from the storage zone (STOR-02).

        Args:
            path: Source path within the zone (e.g. ``"photos/image.jpg"``).

        Returns:
            Raw file bytes.
        """
        url = self._build_url(path)
        headers = self._build_auth_header()
        response = self._sync_request("GET", url, headers=headers)
        return response.content

    def delete(self, path: str) -> None:
        """Delete a file from the storage zone (STOR-03).

        Args:
            path: Path of the file to delete (e.g. ``"photos/image.jpg"``).
        """
        url = self._build_url(path)
        headers = self._build_auth_header()
        self._sync_request("DELETE", url, headers=headers)

    def list(self, path: str = "/") -> list[dict[str, Any]]:
        """List files and directories in the storage zone (STOR-04).

        The path should end with ``"/"`` to indicate a directory listing.
        Listing ``"/"`` returns top-level contents of the zone.

        Args:
            path: Directory path to list (default: ``"/"`` for zone root).

        Returns:
            List of file/directory metadata dicts returned by the Storage API.
        """
        url = self._build_url(path)
        headers = self._build_auth_header()
        response = self._sync_request("GET", url, headers=headers)
        return response.json()
