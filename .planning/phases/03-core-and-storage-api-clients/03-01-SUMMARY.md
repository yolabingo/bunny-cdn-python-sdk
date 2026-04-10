---
phase: 03-core-and-storage-api-clients
plan: 01
subsystem: core-client
tags: [core-api, pull-zones, storage-zones, dns-zones, video-libraries, pagination, concurrency]
dependency_graph:
  requires:
    - src/bunny_cdn_sdk/_client.py
    - src/bunny_cdn_sdk/_pagination.py
    - src/bunny_cdn_sdk/_types.py
    - src/bunny_cdn_sdk/_exceptions.py
  provides:
    - src/bunny_cdn_sdk/core.py
  affects:
    - src/bunny_cdn_sdk/__init__.py  # will wire re-exports in a future plan
tech_stack:
  added: []
  patterns:
    - async generator collection via _collect() helper for iter_* methods
    - asyncio.run(_gather(...)) for concurrent batch fetch
    - pagination_iterator callback pattern for auto-paginating iterators
key_files:
  created:
    - src/bunny_cdn_sdk/core.py
  modified: []
decisions:
  - title: async generator collection helper
    detail: >
      pagination_iterator is an async generator and cannot be passed to asyncio.run()
      directly. Added module-level _collect(agen) coroutine that iterates the async
      generator and returns a list; iter_* methods call asyncio.run(_collect(pagination_iterator(fetch_page))).
  - title: get_pull_zones uses nested fetch_all coroutine
    detail: >
      _gather is an async method; wrapped in a local async fetch_all() coroutine so
      asyncio.run(fetch_all()) correctly awaits all concurrent requests.
  - title: empty-body responses return {}
    detail: >
      DELETE and some POST endpoints return 204/empty body. Added
      `response.json() if response.content else {}` guard to avoid JSONDecodeError.
  - title: base_url from CONTEXT wins over HLD discrepancy
    detail: >
      HLD.md §2 lists https://api.bunny.net but PLAN and CONTEXT explicitly specify
      https://api.bunnycdn.com. Used CONTEXT value; constructor accepts base_url param
      for caller override if needed.
metrics:
  duration: 102s
  completed_date: 2026-04-10
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 0
---

# Phase 03 Plan 01: CoreClient Summary

**One-liner:** CoreClient with 37 public methods across 5 resource groups (Pull Zones, Storage Zones, DNS Zones, Video Libraries, utilities) using asyncio.gather for concurrent batch fetch and pagination_iterator for auto-paginating iterators.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Pull Zone CRUD, extras, concurrent fetch, pagination | f7cfea5 | src/bunny_cdn_sdk/core.py |
| 2 | Storage Zone, DNS Zone, Video Library, utilities | f7cfea5 | src/bunny_cdn_sdk/core.py |

Both tasks were implemented in a single write and committed together.

## What Was Built

`src/bunny_cdn_sdk/core.py` — 614 lines implementing `CoreClient(_BaseClient)` with:

**Pull Zones (12 methods):**
- CRUD: `list_pull_zones`, `get_pull_zone`, `create_pull_zone`, `update_pull_zone`, `delete_pull_zone`
- Iterator: `iter_pull_zones` (auto-pagination via `pagination_iterator`)
- Concurrent batch: `get_pull_zones(ids)` (parallel via `asyncio.gather`)
- Extras: `purge_pull_zone_cache`, `add_custom_hostname`, `remove_custom_hostname`, `add_blocked_ip`, `remove_blocked_ip`

**Storage Zones (6 methods):**
- CRUD: `list_storage_zones`, `get_storage_zone`, `create_storage_zone`, `update_storage_zone`, `delete_storage_zone`
- Iterator: `iter_storage_zones`

**DNS Zones (9 methods):**
- Zone CRUD: `list_dns_zones`, `get_dns_zone`, `create_dns_zone`, `update_dns_zone`, `delete_dns_zone`
- Zone iterator: `iter_dns_zones` (with search support)
- Record management: `add_dns_record`, `update_dns_record`, `delete_dns_record`

**Video Libraries (5 methods):**
- CRUD: `list_video_libraries`, `get_video_library`, `create_video_library`, `update_video_library`, `delete_video_library`

**Utilities (5 methods):**
- `purge_url` (URL-encodes the target URL as query param)
- `get_statistics`, `list_countries`, `list_regions`, `get_billing`

## Decisions Made

**1. async generator collection helper** — `pagination_iterator` is an async generator that must be iterated inside an event loop. Module-level `_collect(agen)` coroutine collects all items; `iter_*` methods call `asyncio.run(_collect(pagination_iterator(fetch_page)))` to produce a synchronous `Iterator`.

**2. get_pull_zones nested coroutine** — `_gather` is async; wrapped in local `fetch_all()` so `asyncio.run(fetch_all())` correctly executes all concurrent requests and returns results in input order.

**3. Empty-body guard** — DELETE and some POST operations return 204 with no body. Added `response.json() if response.content else {}` to avoid `JSONDecodeError`.

**4. Base URL from CONTEXT** — HLD says `api.bunny.net` but PLAN/CONTEXT explicitly state `api.bunnycdn.com`. Used CONTEXT value; constructor accepts `base_url` override param for flexibility.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written, with one implementation detail decision documented above (async generator collection helper required by the existing `pagination_iterator` design).

## Threat Surface Review

No new network endpoints, auth paths, or trust boundaries introduced beyond what the plan's threat model covers. All requests go through `_BaseClient._request()` which enforces HTTPS (hardcoded `https://api.bunnycdn.com`) and TLS certificate validation via httpx defaults.

T-03-03 mitigation applied: `get_pull_zones` docstring documents the recommendation to batch in chunks of 10-20 for large ID lists.

## Self-Check

- FOUND: src/bunny_cdn_sdk/core.py (613 lines, exceeds min_lines: 200)
- FOUND: commit f7cfea5

## Self-Check: PASSED
