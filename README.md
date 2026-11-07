# bunny-cdn-sdk

[![PyPI](https://img.shields.io/pypi/v/bunny-cdn-sdk)](https://pypi.org/project/bunny-cdn-sdk/)

A typed Python SDK for the [Bunny CDN](https://bunny.net) REST API.

This package does not aim to cover every bunny.net API. It currently focuses on a narrow subset of the platform that is useful for CDN, DNS, storage-zone, and basic video-library workflows.

```bash
uv add bunny-cdn-sdk                          # add the SDK to your project
uv tool install 'bunny-cdn-sdk[cli]'          # install the bunnycdn CLI on your PATH
```

<details>
<summary>Table of contents</summary>

- [Scope](#scope)
- [Quick start](#quick-start)
- [CoreClient](#coreclient)
- [StorageClient](#storageclient)
- [ShieldClient](#shieldclient)
- [LoggingClient](#loggingclient)
- [Retry](#retry)
- [Exceptions](#exceptions)
- [CLI](#cli)
- [Requirements](#requirements)

</details>

## Scope

Supported today:

- Core Platform API coverage for pull zones, storage zones, DNS zones, purge, regions, countries, statistics, billing, and stream video library CRUD.
- Edge Storage file operations through `StorageClient`: upload, download, list, and delete.
- Shield (WAF, rate limits, access lists, bot detection, event logs, metrics) through `ShieldClient`.
- Pull zone request logs through `LoggingClient`.
- Load balancers and pull zone edge rules through `CoreClient`.
- Optional CLI coverage for the same implemented SDK operations.

Not supported yet:

- Core Platform API resources outside the current clients, including users, audit logs, search, API keys, and affiliate endpoints.
- Product APIs outside Core, Shield, Logging, and Edge Storage file operations, including Origin Errors, the full Stream API surface beyond video library CRUD, Edge Scripting, and Magic Containers.
- Advanced Storage API capabilities beyond basic file management if Bunny adds endpoints that are not represented by `upload`, `download`, `list`, and `delete`.

If you need an endpoint that exists in the Bunny docs but not in this SDK, that endpoint is currently omitted rather than wrapped behind a partial or unstable abstraction.

## Quick start

```python
from bunny_cdn_sdk import CoreClient, StorageClient

# Core API — pull zones, storage zones, DNS, video libraries
core = CoreClient(api_key="your-api-key")
zones = core.list_pull_zones()  # returns a list directly

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

**Edge Rules**
```python
core.add_or_update_edge_rule(pull_zone_id, **kwargs)
core.delete_edge_rule(pull_zone_id, edge_rule_id)
core.set_edge_rule_enabled(pull_zone_id, edge_rule_id, enabled)
# No list endpoint: read rules from core.get_pull_zone(id)["EdgeRules"]
```

**Load Balancers**
```python
core.list_load_balancers(page=1, count=50)
core.get_load_balancer(id)
core.create_load_balancer(**kwargs)
core.update_load_balancer(id, **kwargs)
core.delete_load_balancer(id)
core.add_origin_group(lb_id, **kwargs)
core.update_origin_group(lb_id, group_id, **kwargs)
core.delete_origin_group(lb_id, group_id)
core.add_origin(lb_id, group_id, **kwargs)
core.update_origin(lb_id, group_id, origin_id, **kwargs)
core.delete_origin(lb_id, group_id, origin_id)
core.get_load_balancer_statistics(id, **kwargs)
core.get_load_balancer_pull_zones(id, **kwargs)
core.get_load_balancer_account_statistics(**kwargs)
core.get_load_balancer_usage(id, **kwargs)
```

**Storage Zones**
```python
core.list_storage_zones()
core.iter_storage_zones()  # all pages
core.get_storage_zone(id)
core.create_storage_zone(**kwargs)
core.update_storage_zone(id, **kwargs)
core.delete_storage_zone(id)
```

**DNS Zones**
```python
core.list_dns_zones()
core.iter_dns_zones()  # all pages
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
core.iter_video_libraries()  # all pages
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

## ShieldClient

```python
from bunny_cdn_sdk import ShieldClient

shield = ShieldClient(api_key="account-api-key")
shield.list_shield_zones()  # returns {"data": [...], "page": {...}, "error": ...}
for rule in shield.iter_rate_limits(zone_id):  # iter_* unwraps "data"
    print(rule)
```

Shield methods return the response envelope as-is. Use `iter_*` to get the items directly.

**Shield Zones**
```python
shield.list_shield_zones(page=1, per_page=10)
shield.iter_shield_zones(per_page=100)
shield.get_shield_zone(id)
shield.get_shield_zone_by_pull_zone(pull_zone_id)
shield.create_shield_zone(pull_zone_id, **kwargs)
shield.update_shield_zone(shield_zone_id, **kwargs)
```

**WAF**
```python
shield.list_waf_rules(zone_id)
shield.list_waf_profiles()
shield.get_waf_enums()
shield.get_waf_engine_config()
shield.list_triggered_waf_rules(zone_id)
shield.review_triggered_waf_rule(zone_id, rule_id, action)
shield.list_custom_waf_rules(zone_id, page=1, per_page=10)
shield.iter_custom_waf_rules(zone_id, per_page=100)
shield.get_custom_waf_rule(id)
shield.create_custom_waf_rule(shield_zone_id, **kwargs)
shield.update_custom_waf_rule(id, **kwargs)
shield.delete_custom_waf_rule(id)
```

**Rate Limits**
```python
shield.list_rate_limits(zone_id, page=1, per_page=10)
shield.iter_rate_limits(zone_id, per_page=100)
shield.get_rate_limit(id)
shield.create_rate_limit(shield_zone_id, **kwargs)
shield.update_rate_limit(id, **kwargs)
shield.delete_rate_limit(id)
```

**Access Lists**
```python
shield.list_access_lists(zone_id)
shield.get_access_list(zone_id, id)
shield.create_access_list(zone_id, **kwargs)
shield.update_access_list(zone_id, id, **kwargs)
shield.update_access_list_configuration(zone_id, id, **kwargs)
shield.delete_access_list(zone_id, id)
```

**Bot Detection, Event Logs, Metrics**
```python
shield.get_bot_detection(zone_id)
shield.update_bot_detection(zone_id, **kwargs)
shield.get_event_logs(zone_id, date, continuation_token)  # date is MM-dd-yyyy
shield.search_event_logs(zone_id, **kwargs)
shield.get_metrics_overview(zone_id)
```

## LoggingClient

```python
from bunny_cdn_sdk import LoggingClient

client = LoggingClient(api_key="account-api-key")
for entry in client.iter_logs(pz_id, **{"from": "2026-11-05T00:00:00Z"}, status="5xx"):
    print(entry)
```

**Request Logs**
```python
client.get_logs(pull_zone_id, **params)  # one page: {"data", "pagination", "query"}
client.iter_logs(pull_zone_id, limit=1000, **params)  # yields every entry
```

`from` is a Python keyword, so pass it through `**{"from": ...}`. Logs are kept for 3 days and a `from`/`to` window can span at most 3 days.

## Retry

```python
from bunny_cdn_sdk import CoreClient, RetryTransport
import httpx2

transport = RetryTransport(max_retries=5, backoff_base=0.5)
core = CoreClient(api_key="...", client=httpx2.Client(transport=transport))
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
uv tool install 'bunny-cdn-sdk[cli]'          # bunnycdn on your PATH
uvx --from 'bunny-cdn-sdk[cli]' bunnycdn --help  # or run once without installing
```

```
bunnycdn --api-key KEY COMMAND

Commands:
  pull-zone      Manage pull zones
  storage-zone   Manage storage zones
  dns-zone       Manage DNS zones
  video-library  Manage video libraries
  storage        Upload, download, list, delete files
  load-balancer  Manage load balancers, origin groups and origins
  shield         Shield zones, WAF, rate limits, access lists, bot detection, event logs, metrics
  logs           Show CDN request logs for a pull zone
  purge          Purge a URL from CDN cache
  stats          CDN statistics per pull zone
  billing        Account billing summary
```

Pull zone edge rules are under `pull-zone edge-rule`.

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
- [httpx2](https://www.python-httpx2.org/)

CLI requirements are optional:

- Install with `uv tool install 'bunny-cdn-sdk[cli]'` (or `uv add 'bunny-cdn-sdk[cli]'` inside a project)
- CLI dependencies: [`typer`](https://typer.tiangolo.com/) and [`rich`](https://rich.readthedocs.io/)
