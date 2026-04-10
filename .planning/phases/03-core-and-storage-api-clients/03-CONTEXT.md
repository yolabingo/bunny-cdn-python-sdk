# Phase 3: Core API & Storage API Clients - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

## Phase Boundary

Implement `CoreClient` (all Pull Zone, Storage Zone, DNS, Video Library, and utility endpoints) and `StorageClient` (upload, download, delete, list with 10-region URL mapping) so the SDK delivers its full v1 surface.

**Two service clients:**
1. **CoreClient** — 27+ methods across 5 resource groups: Pull Zones (CRUD + extras + concurrent fetch + pagination), Storage Zones (CRUD + pagination), DNS Zones (CRUD + records + pagination), Video Libraries (CRUD), and utilities
2. **StorageClient** — 4 operations (upload, download, delete, list) with 10-region base-URL mapping

## Requirements Fulfilled

**Core API (CORE-01 through CORE-11):**
- CORE-01: Pull Zone CRUD (list, get, create, update, delete)
- CORE-02: Pull Zone extras (purge cache, custom hostnames, blocked IPs)
- CORE-03: Concurrent `get_pull_zones([id1, id2])` via `_gather()`
- CORE-04: Pull Zone pagination (`list_pull_zones`, `iter_pull_zones`)
- CORE-05: Storage Zone CRUD
- CORE-06: Storage Zone pagination
- CORE-07: DNS Zone CRUD
- CORE-08: DNS Record management
- CORE-09: DNS Zone pagination
- CORE-10: Video Library CRUD
- CORE-11: Utilities (purge_url, statistics, countries, regions, billing)

**Storage API (STOR-01 through STOR-05):**
- STOR-01: Upload (`bytes | BinaryIO`)
- STOR-02: Download (returns `bytes`)
- STOR-03: Delete
- STOR-04: List (flat directory listing)
- STOR-05: 10-region URL mapping

## Success Criteria

- [ ] `CoreClient("key").list_pull_zones()` and all other CRUD methods return plain `dict` responses without raising on 2xx
- [ ] `CoreClient.get_pull_zones([id1, id2])` issues two requests concurrently (not sequentially) and returns both results in input order
- [ ] `iter_pull_zones()` transparently fetches page 2 when page 1 `HasMoreItems` is true (no manual pagination)
- [ ] `StorageClient("zone", "password", region="ny")` uses `ny.storage.bunnycdn.com` as the base URL; all 10 regions resolve to distinct URLs
- [ ] `StorageClient.upload(path, data)` sends `bytes` and `BinaryIO` payloads without error

## Implementation Decisions

### Locked from Phase 2 & 1 (Not re-decided)

- **Async internals, sync public surface** — All methods use async/await internally, exposed synchronously via `asyncio.run()`
- **_request() chokepoint** — All HTTP calls go through `_BaseClient._request()` which injects headers and maps errors
- **Plain dict responses** — No Pydantic, no dataclasses, no custom classes — return `response.json()` directly
- **Exception mapping** — HTTP status codes map to exception hierarchy (401→`BunnyAuthenticationError`, 404→`BunnyNotFoundError`, 429→`BunnyRateLimitError`, 5xx→`BunnyServerError`)
- **Concurrent batch operations** — Use `_gather()` for concurrent requests, return results in input order

### Phase 3 Implementation Decisions

**CoreClient:**
- **Base URL:** Use `https://api.bunnycdn.com/` (single endpoint for all Core API operations)
- **Constructor:** Accept single parameter `api_key: str`
- **CRUD consistency:** All `create_*()` and `update_*()` methods accept kwargs for request body; pass to `_request()`
- **Pagination defaults:** `list_*()` methods default `page=1, per_page=1000` (Bunny API default); `iter_*()` auto-fetches with same defaults
- **Batch fetch signatures:** `get_pull_zones([id1, id2])` method exists (separate from `get_pull_zone(id)`); returns `list[dict]` in input order
- **Search parameters:** `list_pull_zones(search)`, `iter_pull_zones(search)`, `list_dns_zones(search)`, `iter_dns_zones(search)` all support optional search filter

**StorageClient:**
- **Constructor parameters:** `(zone_name: str, password: str, region: str = "falkenstein")`
- **Base URL mapping table:** Hard-coded 10-region mapping:
  ```
  falkenstein (default) → storage.bunnycdn.com
  de → de.storage.bunnycdn.com
  ny → ny.storage.bunnycdn.com
  la → la.storage.bunnycdn.com
  sg → sg.storage.bunnycdn.com
  syd → syd.storage.bunnycdn.com
  uk → uk.storage.bunnycdn.com
  se → se.storage.bunnycdn.com
  br → br.storage.bunnycdn.com
  jh → jh.storage.bunnycdn.com
  ```
- **Base authentication:** Use HTTP Basic Auth (`Authorization: Basic base64(zone:password)`) on all requests
- **Upload method signature:** `upload(path: str, data: bytes | BinaryIO, content_type: str | None = None)`
  - If `content_type` is provided, set `Content-Type` header
  - If not provided, let httpx infer (or default to `application/octet-stream`)
- **Download method signature:** `download(path: str) -> bytes`
- **Delete method signature:** `delete(path: str) -> None` (returns nothing on success)
- **List method signature:** `list(path: str = "/") -> list[dict]` (returns flat directory listing)
- **File path handling:** All paths passed to Storage API should be URL-encoded by httpx (no manual encoding)

### Claude's Discretion

- **Error handling for partial batch failures:** When `get_pull_zones([id1, id2])` and one request fails, should we raise or return partial results? (Recommend: raise, user handles individual fetches if needed)
- **Pagination with empty results:** When `iter_*()` is called and first page is empty, should it still check `HasMoreItems`? (Recommend: yes, follow the envelope)
- **DNS Record CRUD consolidation:** `add_dns_record`, `update_dns_record`, `delete_dns_record` — should these also be under a `dns_zone_id` parameter? (Yes, per REQUIREMENTS.md)

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### API Specifications & Endpoints
- `.planning/REQUIREMENTS.md` CORE-01 through CORE-11, STOR-01 through STOR-05 — Full endpoint list and signatures
- `.planning/ROADMAP.md` Phase 3 — High-level scope and success criteria
- `docs/HLD.md` §5 — Core API resource groups (if exists)
- `docs/HLD.md` §6 — Storage API specification (if exists)

### Infrastructure & Patterns
- `src/bunny_cdn_sdk/_client.py` — `_BaseClient` interface: `_request()`, `_gather()`, context managers
- `src/bunny_cdn_sdk/_pagination.py` — `pagination_iterator()` callback for `list_*()` and `iter_*()` 
- `src/bunny_cdn_sdk/_exceptions.py` — Exception hierarchy for error mapping
- `CLAUDE.md` — Project constraints (httpx-only, plain dicts, uv, ty)

### Prior Context
- `.planning/phases/01-*/01-CONTEXT.md` — Package and exception decisions
- `.planning/phases/02-*/02-CONTEXT.md` — Base client, pagination, and public API decisions

## Deferred Ideas

None — Phase 3 scope is fully defined. v2 features (Stream API, retry logic, progress callbacks) are deferred to future milestone.

---

*Phase: 03-core-and-storage-api-clients*
*Context gathered: 2026-04-10 from ROADMAP.md, REQUIREMENTS.md, and prior phase decisions*
