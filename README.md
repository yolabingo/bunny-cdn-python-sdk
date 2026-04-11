<!-- generated-by: gsd-doc-writer -->
# bunny-cdn-sdk

A thin, typed Python SDK for the [Bunny CDN](https://bunny.net) REST APIs. Wraps the Core API (Pull Zones, DNS, Storage Zones, Video Libraries, Statistics, Billing) and Storage API in a sync interface backed by async httpx internals.

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)

---

## Install

```bash
pip install bunny-cdn-sdk
```

```bash
uv add bunny-cdn-sdk
```

**Requirements:** Python 3.12+, httpx >= 0.28.1

---

## Quick start

```python
from bunny_cdn_sdk import CoreClient, StorageClient

# Core API — account-level operations
core = CoreClient(api_key="your-account-api-key")
zones = core.list_pull_zones()
print(zones["Items"])

# Storage API — file operations against a storage zone
storage = StorageClient(zone_name="my-zone", password="zone-password", region="ny")
storage.upload("images/photo.jpg", data=open("photo.jpg", "rb"))
```

---

## CoreClient

Covers Pull Zones, Storage Zones (management), DNS Zones, Video Libraries, Statistics, Billing, Purge, API Keys, Countries, and Regions.

### Constructor

```python
CoreClient(
    api_key: str,
    base_url: str = "https://api.bunnycdn.com",
    *,
    client: httpx.AsyncClient | None = None,
    max_retries: int = 0,
    backoff_base: float = 0.5,
)
```

### Representative methods

```python
from bunny_cdn_sdk import CoreClient

core = CoreClient(api_key="your-account-api-key")

# Pull Zones
zones = core.list_pull_zones(page=1, per_page=100)   # single page
zone  = core.get_pull_zone(id=12345)
core.purge_pull_zone_cache(id=12345)

# Concurrent batch fetch — all requests sent concurrently via asyncio.gather
zone_ids = [101, 102, 103, 104, 105]
zones = core.get_pull_zones(zone_ids)  # returns list[dict]

# DNS Zones
dns = core.list_dns_zones()
core.add_dns_record(zone_id=678, Name="www", Type=0, Value="1.2.3.4", Ttl=300)

# Utilities
stats = core.get_statistics(dateFrom="2024-01-01", dateTo="2024-01-31")
core.purge_url(url="https://cdn.example.com/static/app.js")
regions = core.list_regions()
```

Full method reference (37 methods):

| Group | Methods |
|-------|---------|
| Pull Zones | `list_pull_zones`, `iter_pull_zones`, `get_pull_zone`, `get_pull_zones`, `create_pull_zone`, `update_pull_zone`, `delete_pull_zone`, `purge_pull_zone_cache`, `add_custom_hostname`, `remove_custom_hostname`, `add_blocked_ip`, `remove_blocked_ip` |
| Storage Zones | `list_storage_zones`, `iter_storage_zones`, `get_storage_zone`, `create_storage_zone`, `update_storage_zone`, `delete_storage_zone` |
| DNS Zones | `list_dns_zones`, `iter_dns_zones`, `get_dns_zone`, `create_dns_zone`, `update_dns_zone`, `delete_dns_zone`, `add_dns_record`, `update_dns_record`, `delete_dns_record` |
| Video Libraries | `list_video_libraries`, `get_video_library`, `create_video_library`, `update_video_library`, `delete_video_library` |
| Utilities | `purge_url`, `get_statistics`, `list_countries`, `list_regions`, `get_billing` |

---

## StorageClient

Operates against a single Bunny Storage Zone. Auth is handled via HTTP Basic (`zone_name:password`).

### Constructor

```python
StorageClient(
    zone_name: str,
    password: str,
    region: str = "falkenstein",
    *,
    client: httpx.AsyncClient | None = None,
    max_retries: int = 0,
    backoff_base: float = 0.5,
)
```

Valid regions: `falkenstein` (default), `de`, `ny`, `la`, `sg`, `syd`, `uk`, `se`, `br`, `jh`

Raises `ValueError` on unrecognised region.

### Methods

```python
from bunny_cdn_sdk import StorageClient

storage = StorageClient(zone_name="my-zone", password="zone-password", region="ny")

# Upload bytes or a file-like object
storage.upload("images/photo.jpg", data=open("photo.jpg", "rb"))
storage.upload("data/report.json", data=b'{"ok": true}', content_type="application/json")

# Download
raw_bytes = storage.download("images/photo.jpg")

# List directory (flat listing, no pagination)
files = storage.list("images/")   # returns list[dict]
root  = storage.list("/")         # zone root

# Delete
storage.delete("images/photo.jpg")
```

---

## Retry behavior

By default, no retries are performed. Pass `max_retries` to the constructor to enable automatic retry with exponential backoff and full jitter:

```python
from bunny_cdn_sdk import CoreClient, StorageClient

# Up to 3 retries on 429, 5xx, or network errors
core    = CoreClient(api_key="...", max_retries=3)
storage = StorageClient(zone_name="my-zone", password="...", max_retries=3, backoff_base=1.0)
```

`backoff_base` controls the delay cap: delay for retry N is `uniform(0, min(60, base * 2**N))`. For 429 responses, the `Retry-After` header is honoured when present.

### Advanced: custom RetryTransport

For full control (custom connection pools, timeouts, or additional transports), compose `RetryTransport` directly and pass an `httpx.AsyncClient`:

```python
import httpx
from bunny_cdn_sdk import RetryTransport, CoreClient

inner = httpx.AsyncHTTPTransport(limits=httpx.Limits(max_connections=20))
transport = RetryTransport(inner, max_retries=5, backoff_base=0.5)
async_client = httpx.AsyncClient(transport=transport, timeout=60.0)
core = CoreClient(api_key="...", client=async_client)
```

**Note:** Passing both `client=` and `max_retries > 0` raises a `UserWarning` and the `max_retries` argument is ignored — configure `RetryTransport` on your `AsyncClient` directly in that case.

---

## Error handling

All exceptions inherit from `BunnySDKError`:

```
BunnySDKError
├── BunnyAPIError              (any HTTP error — exposes status_code, message, response)
│   ├── BunnyAuthenticationError   (401)
│   ├── BunnyNotFoundError         (404)
│   ├── BunnyRateLimitError        (429)
│   └── BunnyServerError           (5xx)
└── BunnyConnectionError       (network failure)
    └── BunnyTimeoutError      (request timeout)
```

```python
from bunny_cdn_sdk import CoreClient, BunnyNotFoundError, BunnyRateLimitError, BunnySDKError

core = CoreClient(api_key="your-key")

try:
    zone = core.get_pull_zone(id=99999)
except BunnyNotFoundError:
    print("zone not found")
except BunnyRateLimitError as e:
    print(f"rate limited — retry after checking Retry-After header: {e.response.headers.get('retry-after')}")
except BunnySDKError as e:
    print(f"SDK error: {e}")
```

`BunnyAPIError` and its subclasses expose:
- `status_code: int`
- `message: str`
- `response: httpx.Response`

---

## Context manager support

Both sync and async context managers are supported. The underlying `httpx.AsyncClient` is closed on exit.

```python
# Sync context manager
with CoreClient(api_key="...") as core:
    zones = core.list_pull_zones()

# Async context manager
async with CoreClient(api_key="...") as core:
    zones = core.list_pull_zones()
```

When a client is injected via `client=`, the caller owns the client lifecycle and the SDK does not close it on exit.

---

## Pagination

The `list_*` methods return a single page as a dict with `Items`, `CurrentPage`, `TotalItems`, and `HasMoreItems`. The `iter_*` methods return an iterator that fetches pages automatically and yields individual items:

```python
from bunny_cdn_sdk import CoreClient

core = CoreClient(api_key="your-key")

# Single page
result = core.list_pull_zones(page=1, per_page=100)
print(result["TotalItems"], result["HasMoreItems"])

# Auto-paginate — yields one item at a time
for zone in core.iter_pull_zones(per_page=100):
    print(zone["Name"])

for record in core.iter_dns_zones():
    print(record["Domain"])
```

Iterating all pages is lazy: each subsequent page is fetched only when the current page is exhausted.

---

## Return types

All methods return plain `dict` objects (from `response.json()`). No Pydantic models, no dataclasses. Keys match the Bunny CDN API response format exactly.
