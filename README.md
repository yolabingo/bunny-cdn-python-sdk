# bunny-cdn-sdk

A typed Python SDK for the [Bunny CDN](https://bunny.net) REST API.

This package does not aim to cover every bunny.net API. It currently focuses on a narrow subset of the platform that is useful for CDN, DNS, storage-zone, and basic video-library workflows.

```bash
pip install bunny-cdn-sdk
pip install 'bunny-cdn-sdk[cli]'  # includes CLI
```

<details>
<summary>Table of contents</summary>

- [Scope](#scope)
- [Quick start](#quick-start)
- [CoreClient](#coreclient)
- [StorageClient](#storageclient)
- [Retry](#retry)
- [Exceptions](#exceptions)
- [CLI](#cli)
- [Requirements](#requirements)

</details>

## Scope

Supported today:

- Core Platform API coverage for pull zones, storage zones, DNS zones, purge, regions, countries, statistics, billing, and stream video library CRUD.
- Edge Storage file operations through `StorageClient`: upload, download, list, and delete.
- Optional CLI coverage for the same implemented SDK operations.

Not supported yet:

- Core Platform API resources outside the current clients, including users, audit logs, search, API keys, and affiliate endpoints.
- Product APIs outside Core + Edge Storage file operations, including Origin Errors, the full Stream API surface beyond video library CRUD, Shield, Edge Scripting, and Magic Containers.
- Advanced Storage API capabilities beyond basic file management if Bunny adds endpoints that are not represented by `upload`, `download`, `list`, and `delete`.

If you need an endpoint that exists in the Bunny docs but not in this SDK, that endpoint is currently omitted rather than wrapped behind a partial or unstable abstraction.

## Quick start

```python
from bunny_cdn_sdk import CoreClient, StorageClient

# Core API — pull zones, storage zones, DNS, video libraries
core = CoreClient(api_key="your-api-key")
zones_page = core.list_pull_zones()
zones = zones_page["Items"]

# Storage API — file operations
storage = StorageClient(
    zone_name="my-zone",
    password="zone-password",
    region="ny",  # default: falkenstein
)
storage.upload("path/to/file.txt", b"hello")
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
# Fetch specific pull zones concurrently by ID
zones = core.get_pull_zones([123, 456, 789])

# Or iterate through all pull zones across pages
for zone in core.iter_pull_zones():
    print(zone["Name"])
```

## StorageClient

```python
from bunny_cdn_sdk import StorageClient

storage = StorageClient(
    zone_name="my-zone",
    password="zone-password",
    region="falkenstein",  # or: de, ny, la, sg, syd, uk, se, br, jh
)

storage.upload(path: str, data: bytes)
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

CLI requirements are optional:

- Install with `pip install 'bunny-cdn-sdk[cli]'`
- CLI dependencies: [`typer`](https://typer.tiangolo.com/) and [`rich`](https://rich.readthedocs.io/)
