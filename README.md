# bunny-cdn-sdk

A thin, typed Python SDK for the [Bunny CDN](https://bunny.net) REST APIs. Sync interface backed by async httpx internals. Python 3.12+.

## Install

```bash
pip install bunny-cdn-sdk
# or
uv add bunny-cdn-sdk
```

## Quick start

```python
from bunny_cdn_sdk import CoreClient, StorageClient

core = CoreClient(api_key="your-account-api-key")
zones = core.list_pull_zones()

storage = StorageClient(zone_name="my-zone", password="zone-password", region="ny")
storage.upload("images/photo.jpg", data=open("photo.jpg", "rb"))
```

## CoreClient

Covers Pull Zones, Storage Zones (mgmt), DNS Zones, Video Libraries, Statistics, Billing, Purge, API Keys, Countries, and Regions — 37 methods total.

```python
CoreClient(api_key, base_url="https://api.bunnycdn.com", *, client=None, max_retries=0, backoff_base=0.5)
```

Each resource has `list_*` (single page → dict), `iter_*` (auto-paginate → iterator), `get_*`, `create_*`, `update_*`, and `delete_*` variants where applicable.

```python
zones = core.list_pull_zones(page=1, per_page=100)   # {"Items": [...], "TotalItems": N, ...}
for zone in core.iter_pull_zones():                   # yields one item at a time
    print(zone["Name"])

core.purge_url(url="https://cdn.example.com/app.js")
core.get_statistics(dateFrom="2024-01-01", dateTo="2024-01-31")

# Batch fetch — requests issued concurrently
zones = core.get_pull_zones([101, 102, 103])          # list[dict]
```

## StorageClient

```python
StorageClient(zone_name, password, region="falkenstein", *, client=None, max_retries=0, backoff_base=0.5)
```

Valid regions: `falkenstein`, `de`, `ny`, `la`, `sg`, `syd`, `uk`, `se`, `br`, `jh`. Raises `ValueError` on unknown region.

```python
storage.upload("images/photo.jpg", data=open("photo.jpg", "rb"))
storage.upload("data/report.json", data=b'{"ok":true}', content_type="application/json")
raw = storage.download("images/photo.jpg")
files = storage.list("images/")   # list[dict]
storage.delete("images/photo.jpg")
```

## Retry

Pass `max_retries` to enable automatic retry with exponential backoff and full jitter. Retries on 429, 5xx, `ConnectError`, and `TimeoutException`. The `Retry-After` header is honoured on 429 responses.

```python
core = CoreClient(api_key="...", max_retries=3)
storage = StorageClient(zone_name="my-zone", password="...", max_retries=3, backoff_base=1.0)
```

For custom connection pools or timeouts, compose `RetryTransport` directly:

```python
import httpx
from bunny_cdn_sdk import RetryTransport, CoreClient

transport = RetryTransport(httpx.AsyncHTTPTransport(), max_retries=5)
core = CoreClient(api_key="...", client=httpx.AsyncClient(transport=transport, timeout=60.0))
```

> Passing both `client=` and `max_retries > 0` emits a `UserWarning` — the SDK won't modify an injected client's transport. Configure `RetryTransport` directly in that case.

## Error handling

```
BunnySDKError
├── BunnyAPIError           (HTTP error — .status_code, .message, .response)
│   ├── BunnyAuthenticationError  (401)
│   ├── BunnyNotFoundError        (404)
│   ├── BunnyRateLimitError       (429)
│   └── BunnyServerError          (5xx)
└── BunnyConnectionError    (network failure)
    └── BunnyTimeoutError   (timeout)
```

```python
from bunny_cdn_sdk import BunnyNotFoundError, BunnySDKError

try:
    zone = core.get_pull_zone(id=99999)
except BunnyNotFoundError:
    print("not found")
except BunnySDKError as e:
    print(e)
```

## Context managers

```python
with CoreClient(api_key="...") as core:        # sync
    zones = core.list_pull_zones()

async with CoreClient(api_key="...") as core:  # async
    zones = core.list_pull_zones()
```

The underlying `httpx.AsyncClient` is closed on exit unless you injected one via `client=`.
