# bunny-cdn-sdk

A typed Python SDK for the [Bunny CDN](https://bunny.net) REST API.

```bash
pip install bunny-cdn-sdk
pip install 'bunny-cdn-sdk[cli]'  # includes CLI
```

## Quick start

```python
from bunny_cdn_sdk import CoreClient, StorageClient

# Core API — pull zones, storage zones, DNS, video libraries
core = CoreClient(api_key="your-api-key")
zones = core.list_pull_zones()

# Storage API — file operations
storage = StorageClient(
    zone_name="my-zone",
    password="zone-password",
    region="ny",  # default: falkenstein
)
storage.upload(b"hello", "path/to/file.txt")
storage.download("path/to/file.txt")
storage.list("path/")
storage.delete("path/to/file.txt")
```

## CoreClient

```python
core = CoreClient(api_key="...")
```

**Pull Zones**
```python
core.list_pull_zones()
core.get_pull_zone(id)
core.create_pull_zone(**kwargs)
core.update_pull_zone(id, **kwargs)
core.delete_pull_zone(id)
core.purge_pull_zone_cache(id)
core.add_custom_hostname(id, hostname)
core.remove_custom_hostname(id, hostname)
core.add_blocked_ip(id, ip)
core.remove_blocked_ip(id, ip)
```

**Storage Zones**
```python
core.list_storage_zones()
core.get_storage_zone(id)
core.create_storage_zone(**kwargs)
core.update_storage_zone(id, **kwargs)
core.delete_storage_zone(id)
```

**DNS Zones**
```python
core.list_dns_zones()
core.get_dns_zone(id)
core.create_dns_zone(**kwargs)
core.update_dns_zone(id, **kwargs)
core.delete_dns_zone(id)
core.add_dns_record(zone_id, **kwargs)
core.update_dns_record(zone_id, record_id, **kwargs)
core.delete_dns_record(zone_id, record_id)
```

**Video Libraries**
```python
core.list_video_libraries()
core.get_video_library(id)
core.create_video_library(**kwargs)
core.update_video_library(id, **kwargs)
core.delete_video_library(id)
```

**Utilities**
```python
core.purge_url(url)
core.get_statistics(**kwargs)
core.get_billing()
core.list_countries()
core.list_regions()
```

**Concurrent batch fetch**
```python
# Fetch all pages concurrently
zones = core.get_pull_zones()

# Or iterate page by page
for zone in core.iter_pull_zones():
    print(zone["Name"])
```

## StorageClient

```python
from bunny_cdn_sdk import StorageClient

storage = StorageClient(
    zone_name="my-zone",
    password="zone-password",
    region="falkenstein",  # or: ny, la, sg, sy, br, jh, syd, uk, se
)

storage.upload(data: bytes, path: str)
storage.download(path: str) -> bytes
storage.delete(path: str)
storage.list(path: str) -> list[dict]
```

## Retry

```python
from bunny_cdn_sdk import CoreClient, RetryTransport
import httpx

transport = RetryTransport(max_retries=5, backoff_base=0.5)
core = CoreClient(api_key="...", client=httpx.Client(transport=transport))
```

Or via constructor shorthand:

```python
core = CoreClient(api_key="...", max_retries=5, backoff_base=0.5)
```

Retries on: `429 Too Many Requests`, `5xx` server errors, and network failures. Uses exponential backoff with jitter.

## Exceptions

```
BunnySDKError
├── BunnyAPIError
│   ├── BunnyAuthenticationError  # 401
│   ├── BunnyNotFoundError        # 404
│   ├── BunnyRateLimitError       # 429
│   └── BunnyServerError          # 5xx
└── BunnyConnectionError
    └── BunnyTimeoutError
```

```python
from bunny_cdn_sdk import BunnyAPIError, BunnyAuthenticationError

try:
    core.get_pull_zone(id=99999)
except BunnyAuthenticationError:
    print("Invalid API key")
except BunnyAPIError as e:
    print(f"API error {e.status_code}: {e}")
```

## CLI

Install with the `[cli]` extra:

```bash
pip install 'bunny-cdn-sdk[cli]'
```

```
bunnycdn --api-key KEY COMMAND

Commands:
  pull-zone      Manage pull zones
  storage-zone   Manage storage zones
  dns-zone       Manage DNS zones
  video-library  Manage video libraries
  storage        Upload, download, list, delete files
  purge          Purge a URL from CDN cache
  stats          CDN statistics per pull zone
  billing        Account billing summary
```

Auth via env vars (recommended):

```bash
export BUNNY_API_KEY=your-api-key
export BUNNY_STORAGE_KEY=your-storage-password
export BUNNY_STORAGE_ZONE=your-zone-name
export BUNNY_STORAGE_REGION=falkenstein

bunnycdn pull-zone list
bunnycdn storage list path/
bunnycdn --json pull-zone list  # raw JSON output
```

## Requirements

- Python 3.12+
- [httpx](https://www.python-httpx.org/)
