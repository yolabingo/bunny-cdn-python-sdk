# Requirements: bunny-cdn-sdk

**Defined:** 2026-04-10
**Core Value:** A Python developer can `pip install bunny-cdn-sdk`, instantiate a client with their API key, and call methods that map 1:1 to Bunny CDN endpoints — no surprises, no hidden behavior.

## v1 Requirements

### SDK Foundation

- [ ] **INFRA-01**: Base client wraps `httpx.AsyncClient` with sync public surface via `asyncio.run()`
- [ ] **INFRA-02**: `_request()` chokepoint injects `AccessKey` header and `User-Agent: bunny-cdn-sdk/{version}` on every call
- [ ] **INFRA-03**: `_gather()` runs multiple coroutines concurrently via `asyncio.gather()` and returns results as a list
- [ ] **INFRA-04**: Clients support context manager protocol (`with` statement)
- [ ] **INFRA-05**: Clients accept optional `httpx.AsyncClient` for testing and custom transports
- [ ] **INFRA-06**: Exception hierarchy: `BunnySDKError` → `BunnyAPIError` (401 → `BunnyAuthenticationError`, 404 → `BunnyNotFoundError`, 429 → `BunnyRateLimitError`, 5xx → `BunnyServerError`), `BunnyConnectionError` → `BunnyTimeoutError`; all `BunnyAPIError` subclasses expose `status_code`, `message`, `response`
- [ ] **INFRA-07**: `PaginatedResponse` TypedDict models Core API pagination envelope (`Items`, `CurrentPage`, `TotalItems`, `HasMoreItems`)
- [ ] **INFRA-08**: `list_*()` fetches a single page and returns the raw response; `iter_*()` lazily auto-fetches pages and yields individual items — pagination logic decoupled via callback
- [ ] **INFRA-09**: `py.typed` PEP 561 marker present in package
- [ ] **INFRA-10**: `__init__.py` re-exports `CoreClient`, `StorageClient`, and all exception classes

### Core API

- [ ] **CORE-01**: `CoreClient` Pull Zone CRUD — `list_pull_zones`, `get_pull_zone`, `create_pull_zone`, `update_pull_zone`, `delete_pull_zone`
- [ ] **CORE-02**: `CoreClient` Pull Zone extras — `purge_pull_zone_cache`, `add_custom_hostname`, `remove_custom_hostname`, `add_blocked_ip`, `remove_blocked_ip`
- [ ] **CORE-03**: `CoreClient.get_pull_zones(ids)` fetches multiple pull zones concurrently using `_gather()`
- [ ] **CORE-04**: `CoreClient` Pull Zone pagination — `list_pull_zones(page, per_page, search)` + `iter_pull_zones(per_page, search)`
- [ ] **CORE-05**: `CoreClient` Storage Zone CRUD — `list_storage_zones`, `get_storage_zone`, `create_storage_zone`, `update_storage_zone`, `delete_storage_zone`
- [ ] **CORE-06**: `CoreClient` Storage Zone pagination — `list_storage_zones(page, per_page)` + `iter_storage_zones(per_page)`
- [ ] **CORE-07**: `CoreClient` DNS Zone CRUD — `list_dns_zones`, `get_dns_zone`, `create_dns_zone`, `update_dns_zone`, `delete_dns_zone`
- [ ] **CORE-08**: `CoreClient` DNS Record management — `add_dns_record`, `update_dns_record`, `delete_dns_record`
- [ ] **CORE-09**: `CoreClient` DNS Zone pagination — `list_dns_zones(page, per_page, search)` + `iter_dns_zones(per_page, search)`
- [ ] **CORE-10**: `CoreClient` Video Library CRUD — `list_video_libraries`, `get_video_library`, `create_video_library`, `update_video_library`, `delete_video_library`
- [ ] **CORE-11**: `CoreClient` utilities — `purge_url(url)`, `get_statistics(**kwargs)`, `list_countries()`, `list_regions()`, `get_billing()`

### Storage API

- [ ] **STOR-01**: `StorageClient.upload(path, data, content_type?)` accepts `bytes | BinaryIO`
- [ ] **STOR-02**: `StorageClient.download(path)` returns `bytes`
- [ ] **STOR-03**: `StorageClient.delete(path)` removes a file from the storage zone
- [ ] **STOR-04**: `StorageClient.list(path)` returns flat directory listing as `list[dict]` (no pagination)
- [ ] **STOR-05**: `StorageClient` constructor maps `region` parameter to correct base URL across all 10 supported regions (default Falkenstein + de, ny, la, sg, syd, uk, se, br, jh)

### Tests

- [ ] **TEST-01**: All exception types tested via `httpx.MockTransport` (401, 404, 429, 5xx, network error, timeout)
- [ ] **TEST-02**: `CoreClient` methods tested with mocked responses covering all endpoints
- [ ] **TEST-03**: `StorageClient` methods tested with mocked responses covering all 4 operations

## v2 Requirements

### Stream API

- **STRM-01**: `StreamClient` Videos CRUD — `list_videos`, `iter_videos`, `get_video`, `create_video`, `update_video`, `delete_video`
- **STRM-02**: `StreamClient.upload_video(video_id, data)` streams video bytes
- **STRM-03**: `StreamClient` Collections CRUD — `list_collections`, `get_collection`, `create_collection`, `update_collection`, `delete_collection`
- **STRM-04**: Stream API pagination (`page`, `itemsPerPage` — camelCase envelope)

### Extended Coverage

- **EXT-01**: Retry logic / exponential backoff via custom transport
- **EXT-02**: File upload progress callbacks
- **EXT-03**: Shield API, Edge Scripting API, Magic Containers API

## Out of Scope

| Feature | Reason |
|---------|--------|
| Response model objects (Pydantic/dataclass) | Plain dicts avoid dependency and schema-change brittleness |
| Rate limit auto-retry on 429 | Thin wrapper — users handle retry policy |
| Webhook signature verification | Outside v1 scope |
| CLI tool | Not a goal for the SDK |
| Response caching | No magic |
| Automatic content-type detection for uploads | Caller responsibility |
| Unified client holding all API keys | Separate clients match Bunny's per-service auth model |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | — | Pending |
| INFRA-02 | — | Pending |
| INFRA-03 | — | Pending |
| INFRA-04 | — | Pending |
| INFRA-05 | — | Pending |
| INFRA-06 | — | Pending |
| INFRA-07 | — | Pending |
| INFRA-08 | — | Pending |
| INFRA-09 | — | Pending |
| INFRA-10 | — | Pending |
| CORE-01 | — | Pending |
| CORE-02 | — | Pending |
| CORE-03 | — | Pending |
| CORE-04 | — | Pending |
| CORE-05 | — | Pending |
| CORE-06 | — | Pending |
| CORE-07 | — | Pending |
| CORE-08 | — | Pending |
| CORE-09 | — | Pending |
| CORE-10 | — | Pending |
| CORE-11 | — | Pending |
| STOR-01 | — | Pending |
| STOR-02 | — | Pending |
| STOR-03 | — | Pending |
| STOR-04 | — | Pending |
| STOR-05 | — | Pending |
| TEST-01 | — | Pending |
| TEST-02 | — | Pending |
| TEST-03 | — | Pending |

**Coverage:**
- v1 requirements: 29 total
- Mapped to phases: 0 (populated by roadmapper)
- Unmapped: 29 ⚠️

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-10 after initial definition*
