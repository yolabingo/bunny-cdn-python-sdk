# Design: bunny-cdn-sdk

## 1. Overview

A thin, typed Python SDK wrapping the Bunny CDN REST APIs using `httpx2`.

**Design principles:**
- Thin wrapper: no caching, no magic — just a clean HTTP client
- **Sync API** — one `httpx2.Client` per SDK client; batch methods fan out on a `ThreadPoolExecutor` (max 20 workers) where concurrency helps
- Type-annotated throughout (PEP 561 `py.typed` marker)
- Return plain dicts from `response.json()`, not model objects
- Each API service is a separate client with its own credentials
- Optional retry with exponential backoff via `max_retries` constructor kwarg or a composable `RetryTransport`

## 2. Bunny CDN API Landscape

| API | Base URL | Auth Key | Scope |
|-----|----------|----------|-------|
| **Core** | `https://api.bunny.net` | Account API key | Pull Zones, Edge Rules, Load Balancers, Storage Zones (mgmt), DNS Zones, Video Libraries (mgmt), Statistics, Billing, Purge, API Keys, Countries, Regions |
| **Storage** | `https://{region}.storage.bunnycdn.com` | Storage zone password | Upload, Download, Delete, List files |
| **Shield** | `https://api.bunny.net/shield` | Account API key | Shield zones, WAF rules and custom rules, rate limits, access lists, bot detection, event logs, metrics |
| **Logging** | `https://logging.bunnycdn.com` | Account API key | Pull zone request logs (v2 JSON) |
| **Stream** | `https://video.bunnycdn.com` | Library API key | Videos (CRUD + upload), Collections |

Edge Scripting and Magic Containers share the Core base URL and account API key — deferred to a future version.

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
    _client.py           # Base HTTP client (auth, error mapping, context manager)
    _exceptions.py       # Exception hierarchy
    _types.py            # TypedDict definitions (pagination envelopes)
    _pagination.py       # Page/item iterators
    _retry.py            # RetryTransport (composable httpx2 transport)
    core.py              # CoreClient
    storage.py           # StorageClient
    shield.py            # ShieldClient
    logs.py              # LoggingClient
    py.typed             # PEP 561 marker
    cli/                 # `bunnycdn` Typer CLI (optional `cli` extra: typer + rich)
```

Private modules (`_`-prefixed) are internal. Users import from the package root.

Note: `stream.py` (StreamClient) is planned but not yet implemented — deferred to a future milestone.

## 4. Client Architecture

### Base Client (`_client.py`)

A single `_BaseClient` class that:
- Uses a sync `httpx2.Client` for all HTTP calls
- Provides `_request()` — single chokepoint for all HTTP calls (auth injection, error mapping)
- Provides `_json()` — `_request()` + `.json()`, returning `{}` for an empty body
- Injects `AccessKey` header and `User-Agent: bunny-cdn-sdk/{version}`
- Context manager support (`with` client); `close()` only closes a client the SDK created
- Accepts optional `httpx2.Client` param for dependency injection (testing, custom transports)
- Supports optional automatic retry via `max_retries` / `backoff_base` constructor kwargs

Constructor signature:

```python
_BaseClient(
    api_key: str,
    client: httpx2.Client | None = None,
    *,
    max_retries: int = 0,
    backoff_base: float = 0.5,
)
```

When `client` is provided, `max_retries` is ignored (a `UserWarning` is emitted) — the caller must configure `RetryTransport` on their `Client` directly. When `max_retries > 0` and no `client` is provided, a `RetryTransport`-wrapped `Client` is created automatically.

### Concurrency Model

Single requests are plain blocking calls. Batch methods fan out on a thread pool sharing the one `httpx2.Client` (which is thread-safe):

```python
def get_pull_zones(self, ids: list[int]) -> list[dict]:
    def fetch_one(id: int) -> dict:
        return self._json("GET", f"{self.base_url}/pullzone/{id}")

    with ThreadPoolExecutor(max_workers=max(1, min(len(ids), 20))) as pool:
        return list(pool.map(fetch_one, ids))
```

### Service Clients

```
CoreClient(_BaseClient)        — base_url = "https://api.bunny.net"
StorageClient(_BaseClient)     — base_url = "https://{region}.storage.bunnycdn.com"
ShieldClient(_BaseClient)      — base_url = "https://api.bunny.net/shield"
LoggingClient(_BaseClient)     — base_url = "https://logging.bunnycdn.com"
StreamClient(_BaseClient)      — base_url = "https://video.bunnycdn.com"  [planned]
```

Each service sets its own `base_url` default. Users provide the appropriate API key.

### RetryTransport (`_retry.py`)

A composable `httpx2.BaseTransport` that wraps any inner transport and adds retry logic:

- **Retry triggers:** HTTP 429, `httpx2.ConnectError`, connect timeouts; HTTP 5xx and other `httpx2.TimeoutException`s only for GET/HEAD/OPTIONS/DELETE (POST/PUT may already have been applied — Bunny uses PUT to create DNS records)
- **Backoff:** full-jitter exponential — `uniform(0, min(60, base * 2**attempt))`
- **429 handling:** honours `Retry-After` header (integer seconds or HTTP-date format)
- `max_retries=3` means up to 4 total attempts (initial + 3 retries)

Used automatically when `max_retries > 0` is passed to a service client constructor. Can also be composed manually for advanced cases (custom connection pools, timeouts).

## 5. Service: Core API (`core.py`)

Constructor: `CoreClient(api_key: str, base_url: str = "https://api.bunny.net", *, client: httpx2.Client | None = None, max_retries: int = 0, backoff_base: float = 0.5)`

### Pull Zones

| Method | HTTP | Path |
|--------|------|------|
| `list_pull_zones(search)` | GET | `/pullzone` (returns a plain list, unpaginated) |
| `iter_pull_zones(search)` | GET | `/pullzone` (yields from `list_pull_zones`) |
| `get_pull_zone(id)` | GET | `/pullzone/{id}` |
| `get_pull_zones(ids)` | GET | `/pullzone/{id}` (concurrent) |
| `create_pull_zone(**kwargs)` | POST | `/pullzone` |
| `update_pull_zone(id, **kwargs)` | POST | `/pullzone/{id}` |
| `delete_pull_zone(id)` | DELETE | `/pullzone/{id}` |
| `purge_pull_zone_cache(id, **kwargs)` | POST | `/pullzone/{id}/purgeCache` |
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
| `iter_video_libraries(per_page)` | GET | `/videolibrary` (auto-paginate) |
| `get_video_library(id)` | GET | `/videolibrary/{id}` |
| `create_video_library(**kwargs)` | POST | `/videolibrary` |
| `update_video_library(id, **kwargs)` | POST | `/videolibrary/{id}` |
| `delete_video_library(id)` | DELETE | `/videolibrary/{id}` |

### Utilities

| Method | HTTP | Path |
|--------|------|------|
| `purge_url(url, **kwargs)` | POST | `/purge?url={url}` |
| `get_statistics(**kwargs)` | GET | `/statistics` |
| `list_countries()` | GET | `/country` |
| `list_regions()` | GET | `/region` |
| `get_billing()` | GET | `/billing` |

### Edge Rules

| Method | HTTP | Path |
|--------|------|------|
| `add_or_update_edge_rule(pull_zone_id, **kwargs)` | POST | `/pullzone/{pull_zone_id}/edgerules/addOrUpdate` |
| `delete_edge_rule(pull_zone_id, edge_rule_id)` | DELETE | `/pullzone/{pull_zone_id}/edgerules/{edge_rule_id}` |
| `set_edge_rule_enabled(pull_zone_id, edge_rule_id, enabled)` | POST | `/pullzone/{pull_zone_id}/edgerules/{edge_rule_id}/setEdgeRuleEnabled` |

There is no list endpoint. Edge rules are read from `get_pull_zone(id)["EdgeRules"]`.

### Load Balancers

| Method | HTTP | Path |
|--------|------|------|
| `list_load_balancers(page, count)` | GET | `/loadbalancer` |
| `get_load_balancer(id)` | GET | `/loadbalancer/{id}` |
| `create_load_balancer(**kwargs)` | POST | `/loadbalancer` |
| `update_load_balancer(id, **kwargs)` | POST | `/loadbalancer/{id}` |
| `delete_load_balancer(id)` | DELETE | `/loadbalancer/{id}` |
| `add_origin_group(lb_id, **kwargs)` | POST | `/loadbalancer/{lb_id}/origingroup` |
| `update_origin_group(lb_id, group_id, **kwargs)` | POST | `/loadbalancer/{lb_id}/origingroup/{group_id}` |
| `delete_origin_group(lb_id, group_id)` | DELETE | `/loadbalancer/{lb_id}/origingroup/{group_id}` |
| `add_origin(lb_id, group_id, **kwargs)` | POST | `/loadbalancer/{lb_id}/origingroup/{group_id}/origin` |
| `update_origin(lb_id, group_id, origin_id, **kwargs)` | POST | `/loadbalancer/{lb_id}/origingroup/{group_id}/origin/{origin_id}` |
| `delete_origin(lb_id, group_id, origin_id)` | DELETE | `/loadbalancer/{lb_id}/origingroup/{group_id}/origin/{origin_id}` |
| `get_load_balancer_statistics(id, **kwargs)` | GET | `/loadbalancer/{id}/statistics` |
| `get_load_balancer_pull_zones(id, **kwargs)` | GET | `/loadbalancer/{id}/pullzones` |
| `get_load_balancer_account_statistics(**kwargs)` | GET | `/loadbalancer/statistics` |
| `get_load_balancer_usage(id, **kwargs)` | GET | `/loadbalancer/{id}/usage` |

## 6. Service: Storage API (`storage.py`)

Constructor: `StorageClient(zone_name: str, password: str, region: str = "falkenstein", *, client: httpx2.Client | None = None, max_retries: int = 0, backoff_base: float = 0.5)`

Raises `ValueError` on unrecognised region. Auth sends the zone password in the `AccessKey` header. Paths are URL-quoted and a leading `/` is stripped.

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

- `upload()` accepts `bytes | BinaryIO`, returns the API's JSON `dict`
- `download()` returns `bytes`
- `delete()` returns `None`
- `list()` returns `list[dict]` (no pagination — flat directory listing)

## 6a. Service: Shield API (`shield.py`)

Constructor: `ShieldClient(api_key: str, base_url: str = "https://api.bunny.net/shield", *, client: httpx2.Client | None = None, max_retries: int = 0, backoff_base: float = 0.5)`

Responses are `{data, page, error}` envelopes returned as-is. The `iter_*` methods unwrap `data` and follow `page.nextPage`.

### Shield Zones

| Method | HTTP | Path |
|--------|------|------|
| `list_shield_zones(page, per_page)` | GET | `/shield-zones` |
| `iter_shield_zones(per_page)` | GET | `/shield-zones` (auto-paginate) |
| `get_shield_zone(id)` | GET | `/shield-zone/{id}` |
| `get_shield_zone_by_pull_zone(pull_zone_id)` | GET | `/shield-zone/get-by-pullzone/{pull_zone_id}` |
| `create_shield_zone(pull_zone_id, **kwargs)` | POST | `/shield-zone` |
| `update_shield_zone(shield_zone_id, **kwargs)` | PATCH | `/shield-zone` (ID in body) |

### WAF

| Method | HTTP | Path |
|--------|------|------|
| `list_waf_rules(zone_id)` | GET | `/waf/rules/{zone_id}` |
| `list_waf_profiles()` | GET | `/waf/profiles` |
| `get_waf_enums()` | GET | `/waf/enums` |
| `get_waf_engine_config()` | GET | `/waf/engine-config` |
| `list_triggered_waf_rules(zone_id)` | GET | `/waf/rules/review-triggered/{zone_id}` |
| `review_triggered_waf_rule(zone_id, rule_id, action)` | POST | `/waf/rules/review-triggered/{zone_id}` |
| `list_custom_waf_rules(zone_id, page, per_page)` | GET | `/waf/custom-rules/{zone_id}` |
| `iter_custom_waf_rules(zone_id, per_page)` | GET | `/waf/custom-rules/{zone_id}` (auto-paginate) |
| `get_custom_waf_rule(id)` | GET | `/waf/custom-rule/{id}` |
| `create_custom_waf_rule(shield_zone_id, **kwargs)` | POST | `/waf/custom-rule` |
| `update_custom_waf_rule(id, **kwargs)` | PATCH | `/waf/custom-rule/{id}` |
| `delete_custom_waf_rule(id)` | DELETE | `/waf/custom-rule/{id}` |

### Rate Limits

| Method | HTTP | Path |
|--------|------|------|
| `list_rate_limits(zone_id, page, per_page)` | GET | `/rate-limits/{zone_id}` |
| `iter_rate_limits(zone_id, per_page)` | GET | `/rate-limits/{zone_id}` (auto-paginate) |
| `get_rate_limit(id)` | GET | `/rate-limit/{id}` |
| `create_rate_limit(shield_zone_id, **kwargs)` | POST | `/rate-limit` |
| `update_rate_limit(id, **kwargs)` | PATCH | `/rate-limit/{id}` |
| `delete_rate_limit(id)` | DELETE | `/rate-limit/{id}` |

### Access Lists

| Method | HTTP | Path |
|--------|------|------|
| `list_access_lists(zone_id)` | GET | `/shield-zone/{zone_id}/access-lists` |
| `get_access_list(zone_id, id)` | GET | `/shield-zone/{zone_id}/access-lists/{id}` |
| `create_access_list(zone_id, **kwargs)` | POST | `/shield-zone/{zone_id}/access-lists` |
| `update_access_list(zone_id, id, **kwargs)` | PATCH | `/shield-zone/{zone_id}/access-lists/{id}` |
| `update_access_list_configuration(zone_id, id, **kwargs)` | PATCH | `/shield-zone/{zone_id}/access-lists/configurations/{id}` |
| `delete_access_list(zone_id, id)` | DELETE | `/shield-zone/{zone_id}/access-lists/{id}` |

### Bot Detection, Event Logs, Metrics

| Method | HTTP | Path |
|--------|------|------|
| `get_bot_detection(zone_id)` | GET | `/shield-zone/{zone_id}/bot-detection` |
| `update_bot_detection(zone_id, **kwargs)` | PATCH | `/shield-zone/{zone_id}/bot-detection` |
| `get_event_logs(zone_id, date, continuation_token)` | GET | `/event-logs/{zone_id}/{date}/{continuation_token}` |
| `search_event_logs(zone_id, **kwargs)` | POST | `/event-logs/{zone_id}/search` |
| `get_metrics_overview(zone_id)` | GET | `/metrics/overview/{zone_id}` |

Quirks:
- `get_event_logs` takes `date` as `MM-dd-yyyy`.
- Shield responses are returned unwrapped (`{data, page, error}`). Only `iter_*` strip the envelope.

## 6b. Service: Logging API (`logs.py`)

Constructor: `LoggingClient(api_key: str, base_url: str = "https://logging.bunnycdn.com", *, client: httpx2.Client | None = None, max_retries: int = 0, backoff_base: float = 0.5)`

| Method | HTTP | Path |
|--------|------|------|
| `get_logs(pull_zone_id, **params)` | GET | `/v2/pullzones/{pull_zone_id}/logs` |
| `iter_logs(pull_zone_id, limit, **params)` | GET | `/v2/pullzones/{pull_zone_id}/logs` (offset pagination) |

Quirks:
- `get_logs` returns `{data, pagination, query}`. `iter_logs` yields the `data` items.
- `from` is a Python keyword, so callers pass it as `**{"from": ...}`.
- `iter_logs` pins the `from`/`to` window the API resolved on the first page, so the window does not shift between pages.
- Only the v2 JSON endpoint is wrapped. The v1 legacy endpoint is not wrapped.

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

All `BunnyAPIError` subclasses expose: `status_code`, `message`, `response` (the raw `httpx2.Response`).

## 9. Pagination (`_pagination.py`)

Two patterns exposed on service methods:
- `list_*()` — fetch a single page, return the paginated response dict
- `iter_*()` — lazy iterator that auto-fetches pages, yields individual items

Iterators accept a callback (the page-fetcher function), decoupling pagination logic from specific endpoints.

## 10. Public API (`__init__.py`)

```python
from bunny_cdn_sdk import CoreClient, StorageClient, ShieldClient, LoggingClient
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

# Core API — concurrent batch requests (thread pool)
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
import httpx2
from bunny_cdn_sdk import RetryTransport, CoreClient

inner = httpx2.HTTPTransport()
transport = RetryTransport(inner, max_retries=3, backoff_base=0.5)
client = httpx2.Client(transport=transport)
core = CoreClient(api_key="account-key", client=client)
```

## 12. Out of Scope (v1)

- Response model objects (Pydantic/dataclass) — return plain dicts
- Rate limit handling / auto-retry on 429 beyond what RetryTransport provides
- Webhook signature verification
- Response caching
- Edge Scripting API, Magic Containers API
- File upload progress callbacks
- Automatic content-type detection for uploads
- A unified "Bunny" client holding all API keys
- StreamClient (`stream.py`) — deferred to v1.1

## 13. Implementation Order

1. `_exceptions.py` — no deps, test immediately
2. `_client.py` — `_BaseClient` with sync `httpx2.Client`, error mapping, context manager
3. `_types.py` — `PaginatedResponse` TypedDict
4. `_pagination.py` — iterators
5. `_retry.py` — `RetryTransport`
6. `storage.py` — simplest surface (4 operations, no pagination), validates base client design
7. `core.py` — largest surface, exercises pagination and batch concurrency
8. `stream.py` — different base URL + auth + camelCase pagination [planned]
9. `__init__.py` — wire up re-exports
10. Tests throughout using `httpx2.MockTransport`
11. `cli/` — `bunnycdn` Typer CLI over the SDK
