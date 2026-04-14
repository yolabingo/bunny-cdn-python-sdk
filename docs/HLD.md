# High-Level Design: bunny-cdn-sdk

## 1. Overview

A thin, typed Python SDK wrapping the Bunny CDN REST APIs using `httpx`.

**Design principles:**
- Thin wrapper: no caching, no magic — just a clean HTTP client
- **Sync public API, async internals** — users call simple sync methods; the SDK uses `httpx.AsyncClient` + `asyncio.gather` internally to send concurrent requests where beneficial
- Type-annotated throughout (PEP 561 `py.typed` marker)
- Return plain dicts from `response.json()`, not model objects
- Each API service is a separate client with its own credentials
- Optional retry with exponential backoff via `max_retries` constructor kwarg or a composable `RetryTransport`

## 2. Bunny CDN API Landscape

| API | Base URL | Auth Key | Scope |
|-----|----------|----------|-------|
| **Core** | `https://api.bunnycdn.com` | Account API key | Pull Zones, Storage Zones (mgmt), DNS Zones, Video Libraries (mgmt), Statistics, Billing, Purge, API Keys, Countries, Regions |
| **Storage** | `https://{region}.storage.bunnycdn.com` | Storage zone password | Upload, Download, Delete, List files |
| **Stream** | `https://video.bunnycdn.com` | Library API key | Videos (CRUD + upload), Collections |

Shield, Edge Scripting, and Magic Containers share the Core base URL and account API key — deferred to a future version.

### Authentication

All APIs use the same header: `AccessKey: <key>`. The key value differs per service.

### Pagination (Core API)

- Query params: `page` (int), `perPage` (int, 5-1000)
- `page=0`: returns plain JSON array (all items)
- `page>=1`: returns `{"Items": [...], "CurrentPage": int, "TotalItems": int, "HasMoreItems": bool}`

### Pagination (Stream API)

- Query params: `page` (int), `itemsPerPage` (int)
- Always returns: `{"items": [...], "currentPage": int, "totalItems": int, "itemsPerPage": int}`
- Note: camelCase fields vs Core's PascalCase

### Error Responses

- `401` — bad API key
- `404` — resource not found
- `429` — rate limited (undocumented but observed)
- `5xx` — server error

## 3. Package Structure

```
src/bunny_cdn_sdk/
    __init__.py          # Public re-exports
    _client.py           # Base HTTP client (async internals, sync public surface)
    _exceptions.py       # Exception hierarchy
    _types.py            # TypedDict definitions (pagination envelopes)
    _pagination.py       # Page/item iterators
    _retry.py            # RetryTransport (composable httpx async transport)
    core.py              # CoreClient
    storage.py           # StorageClient
    py.typed             # PEP 561 marker
```

Private modules (`_`-prefixed) are internal. Users import from the package root.

Note: `stream.py` (StreamClient) is planned but not yet implemented — deferred to a future milestone.

## 4. Client Architecture

### Base Client (`_client.py`)

A single `_BaseClient` class that:
- Uses `httpx.AsyncClient` internally for all HTTP calls
- Exposes sync methods by running async operations through `asyncio.run()`
- Provides `_request()` — single async chokepoint for all HTTP calls (auth injection, error mapping)
- Provides `_request_json()` — `_request()` + `.json()`
- Provides `_gather(*coroutines)` — runs multiple requests concurrently via `asyncio.gather`, returns results as a list. This is the key enabler for batch operations.
- Injects `AccessKey` header and `User-Agent: bunny-cdn-sdk/{version}`
- Context manager support (`with` client, `async with` client)
- Accepts optional `httpx.AsyncClient` param for dependency injection (testing, custom transports)
- Supports optional automatic retry via `max_retries` / `backoff_base` constructor kwargs

Constructor signature:

```python
_BaseClient(
    api_key: str,
    client: httpx.AsyncClient | None = None,
    *,
    max_retries: int = 0,
    backoff_base: float = 0.5,
)
```

When `client` is provided, `max_retries` is ignored (a `UserWarning` is emitted) — the caller must configure `RetryTransport` on their `AsyncClient` directly. When `max_retries > 0` and no `client` is provided, a `RetryTransport`-wrapped `AsyncClient` is created automatically.

### Concurrency Model

Single requests go through `asyncio.run()` with minimal overhead. Batch methods use `asyncio.gather()` for concurrent execution:

```python
# Internal pattern — user never sees async
def get_pull_zones(self, ids: list[int]) -> list[dict]:
    """Fetch multiple pull zones concurrently."""
    return self._gather(
        self._request_json("GET", f"/pullzone/{id}") for id in ids
    )
```

### Service Clients

```
CoreClient(_BaseClient)        — base_url = "https://api.bunnycdn.com"
StorageClient(_BaseClient)     — base_url = "https://{region}.storage.bunnycdn.com"
StreamClient(_BaseClient)      — base_url = "https://video.bunnycdn.com"  [planned]
```

Each service sets its own `base_url` default. Users provide the appropriate API key.

### RetryTransport (`_retry.py`)

A composable `httpx.AsyncBaseTransport` that wraps any inner transport and adds retry logic:

- **Retry triggers:** HTTP 429, HTTP 5xx, `httpx.ConnectError`, `httpx.TimeoutException`
- **Backoff:** full-jitter exponential — `uniform(0, min(60, base * 2**attempt))`
- **429 handling:** honours `Retry-After` header (integer seconds or HTTP-date format)
- `max_retries=3` means up to 4 total attempts (initial + 3 retries)

Used automatically when `max_retries > 0` is passed to a service client constructor. Can also be composed manually for advanced cases (custom connection pools, timeouts).

## 5. Service: Core API (`core.py`)

Constructor: `CoreClient(api_key: str, base_url: str = "https://api.bunnycdn.com", *, client: httpx.AsyncClient | None = None, max_retries: int = 0, backoff_base: float = 0.5)`

### Pull Zones

| Method | HTTP | Path |
|--------|------|------|
| `list_pull_zones(page, per_page, search)` | GET | `/pullzone` |
| `iter_pull_zones(per_page, search)` | GET | `/pullzone` (auto-paginate) |
| `get_pull_zone(id)` | GET | `/pullzone/{id}` |
| `get_pull_zones(ids)` | GET | `/pullzone/{id}` (concurrent) |
| `create_pull_zone(**kwargs)` | POST | `/pullzone` |
| `update_pull_zone(id, **kwargs)` | POST | `/pullzone/{id}` |
| `delete_pull_zone(id)` | DELETE | `/pullzone/{id}` |
| `purge_pull_zone_cache(id)` | POST | `/pullzone/{id}/purgeCache` |
| `add_custom_hostname(id, hostname)` | POST | `/pullzone/{id}/addHostname` |
| `remove_custom_hostname(id, hostname)` | DELETE | `/pullzone/{id}/removeHostname` |
| `add_blocked_ip(id, ip)` | POST | `/pullzone/{id}/addBlockedIp` |
| `remove_blocked_ip(id, ip)` | POST | `/pullzone/{id}/removeBlockedIp` |

### Storage Zones (Management)

| Method | HTTP | Path |
|--------|------|------|
| `list_storage_zones(page, per_page)` | GET | `/storagezone` |
| `iter_storage_zones(per_page)` | GET | `/storagezone` (auto-paginate) |
| `get_storage_zone(id)` | GET | `/storagezone/{id}` |
| `create_storage_zone(**kwargs)` | POST | `/storagezone` |
| `update_storage_zone(id, **kwargs)` | POST | `/storagezone/{id}` |
| `delete_storage_zone(id)` | DELETE | `/storagezone/{id}` |

### DNS Zones

| Method | HTTP | Path |
|--------|------|------|
| `list_dns_zones(page, per_page, search)` | GET | `/dnszone` |
| `iter_dns_zones(per_page, search)` | GET | `/dnszone` (auto-paginate) |
| `get_dns_zone(id)` | GET | `/dnszone/{id}` |
| `create_dns_zone(**kwargs)` | POST | `/dnszone` |
| `update_dns_zone(id, **kwargs)` | POST | `/dnszone/{id}` |
| `delete_dns_zone(id)` | DELETE | `/dnszone/{id}` |
| `add_dns_record(zone_id, **kwargs)` | PUT | `/dnszone/{zone_id}/records` |
| `update_dns_record(zone_id, record_id, **kwargs)` | POST | `/dnszone/{zone_id}/records/{record_id}` |
| `delete_dns_record(zone_id, record_id)` | DELETE | `/dnszone/{zone_id}/records/{record_id}` |

### Video Libraries (Management via Core API)

| Method | HTTP | Path |
|--------|------|------|
| `list_video_libraries(page, per_page)` | GET | `/videolibrary` |
| `get_video_library(id)` | GET | `/videolibrary/{id}` |
| `create_video_library(**kwargs)` | POST | `/videolibrary` |
| `update_video_library(id, **kwargs)` | POST | `/videolibrary/{id}` |
| `delete_video_library(id)` | DELETE | `/videolibrary/{id}` |

### Utilities

| Method | HTTP | Path |
|--------|------|------|
| `purge_url(url)` | POST | `/purge?url={url}` |
| `get_statistics(**kwargs)` | GET | `/statistics` |
| `list_countries()` | GET | `/country` |
| `list_regions()` | GET | `/region` |
| `get_billing()` | GET | `/billing` |

## 6. Service: Storage API (`storage.py`)

Constructor: `StorageClient(zone_name: str, password: str, region: str = "falkenstein", *, client: httpx.AsyncClient | None = None, max_retries: int = 0, backoff_base: float = 0.5)`

Raises `ValueError` on unrecognised region. Auth uses both `AccessKey` header and `Authorization: Basic base64(zone_name:password)`.

Region maps to base URL:
- `"falkenstein"` (default) → `https://storage.bunnycdn.com`
- `"de"` → `https://de.storage.bunnycdn.com`
- `"ny"` → `https://ny.storage.bunnycdn.com`
- `"la"` → `https://la.storage.bunnycdn.com`
- `"sg"` → `https://sg.storage.bunnycdn.com`
- `"syd"` → `https://syd.storage.bunnycdn.com`
- `"uk"` → `https://uk.storage.bunnycdn.com`
- `"se"` → `https://se.storage.bunnycdn.com`
- `"br"` → `https://br.storage.bunnycdn.com`
- `"jh"` → `https://jh.storage.bunnycdn.com`

URL pattern: `/{storage_zone}/{path}`

| Method | HTTP | Path |
|--------|------|------|
| `upload(path, data, content_type?)` | PUT | `/{zone}/{path}` |
| `download(path)` | GET | `/{zone}/{path}` |
| `delete(path)` | DELETE | `/{zone}/{path}` |
| `list(path)` | GET | `/{zone}/{path}/` |

- `upload()` accepts `bytes | BinaryIO`
- `download()` returns `bytes`
- `list()` returns `list[dict]` (no pagination — flat directory listing)

## 7. Service: Stream API (`stream.py`)

**Status: planned, not yet implemented.**

Constructor: `StreamClient(api_key: str, library_id: int, *, base_url: str = "https://video.bunnycdn.com", timeout: float = 30.0)`

All paths are scoped to `/library/{library_id}/`.

### Videos

| Method | HTTP | Path |
|--------|------|------|
| `list_videos(page, items_per_page, search, collection, order_by)` | GET | `/library/{id}/videos` |
| `iter_videos(items_per_page, search, collection, order_by)` | GET | auto-paginate |
| `get_video(video_id)` | GET | `/library/{id}/videos/{video_id}` |
| `create_video(title, **kwargs)` | POST | `/library/{id}/videos` |
| `update_video(video_id, **kwargs)` | POST | `/library/{id}/videos/{video_id}` |
| `delete_video(video_id)` | DELETE | `/library/{id}/videos/{video_id}` |
| `upload_video(video_id, data)` | PUT | `/library/{id}/videos/{video_id}` |

### Collections

| Method | HTTP | Path |
|--------|------|------|
| `list_collections(page, items_per_page)` | GET | `/library/{id}/collections` |
| `get_collection(collection_id)` | GET | `/library/{id}/collections/{cid}` |
| `create_collection(**kwargs)` | POST | `/library/{id}/collections` |
| `update_collection(collection_id, **kwargs)` | POST | `/library/{id}/collections/{cid}` |
| `delete_collection(collection_id)` | DELETE | `/library/{id}/collections/{cid}` |

## 8. Exception Hierarchy (`_exceptions.py`)

```
BunnySDKError
├── BunnyAPIError              (any HTTP error response)
│   ├── BunnyAuthenticationError   (401)
│   ├── BunnyNotFoundError         (404)
│   ├── BunnyRateLimitError        (429)
│   └── BunnyServerError           (5xx)
├── BunnyConnectionError       (network failure)
│   └── BunnyTimeoutError      (request timeout)
```

All `BunnyAPIError` subclasses expose: `status_code`, `message`, `response` (the raw `httpx.Response`).

## 9. Pagination (`_pagination.py`)

Two patterns exposed on service methods:
- `list_*()` — fetch a single page, return the paginated response dict
- `iter_*()` — lazy iterator that auto-fetches pages, yields individual items

Iterators accept a callback (the page-fetcher function), decoupling pagination logic from specific endpoints.

## 10. Public API (`__init__.py`)

```python
from bunny_cdn_sdk import CoreClient, StorageClient
from bunny_cdn_sdk import RetryTransport
from bunny_cdn_sdk import BunnyAPIError, BunnyAuthenticationError, ...
```

## 11. Usage Examples

```python
# Core API — single requests
from bunny_cdn_sdk import CoreClient

with CoreClient(api_key="account-key") as client:
    for zone in client.iter_pull_zones():
        print(zone["Name"])

# Core API — concurrent batch requests (async internally, sync to caller)
with CoreClient(api_key="account-key") as client:
    zone_ids = [101, 102, 103, 104, 105]
    zones = client.get_pull_zones(zone_ids)  # 5 requests sent concurrently

# Core API — with retries
core = CoreClient(api_key="account-key", max_retries=3)

# Storage API
from bunny_cdn_sdk import StorageClient

storage = StorageClient(zone_name="my-zone", password="zone-password", region="ny")
storage.upload("images/photo.jpg", data=open("photo.jpg", "rb"))
files = storage.list("images/")

# Advanced: custom RetryTransport
import httpx
from bunny_cdn_sdk import RetryTransport, CoreClient

inner = httpx.AsyncHTTPTransport()
transport = RetryTransport(inner, max_retries=3, backoff_base=0.5)
async_client = httpx.AsyncClient(transport=transport)
core = CoreClient(api_key="account-key", client=async_client)
```

## 12. Out of Scope (v1)

- Response model objects (Pydantic/dataclass) — return plain dicts
- Rate limit handling / auto-retry on 429 beyond what RetryTransport provides
- Webhook signature verification
- CLI tool
- Response caching
- Shield API, Edge Scripting API, Magic Containers API
- File upload progress callbacks
- Automatic content-type detection for uploads
- A unified "Bunny" client holding all API keys
- StreamClient (`stream.py`) — deferred to v1.1

## 13. Implementation Order

1. `_exceptions.py` — no deps, test immediately
2. `_client.py` — `_BaseClient` with async internals, sync surface, `_gather()`, error mapping, context manager
3. `_types.py` — `PaginatedResponse` TypedDict
4. `_pagination.py` — iterators
5. `_retry.py` — `RetryTransport`
6. `storage.py` — simplest surface (4 operations, no pagination), validates base client design
7. `core.py` — largest surface, exercises pagination and batch concurrency
8. `stream.py` — different base URL + auth + camelCase pagination [planned]
9. `__init__.py` — wire up re-exports
10. Tests throughout using `httpx.MockTransport`
