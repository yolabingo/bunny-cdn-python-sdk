---
phase: 03-core-and-storage-api-clients
plan: 02
subsystem: storage-client
tags: [storage-api, basic-auth, region-mapping, upload, download, delete, list]
dependency_graph:
  requires:
    - src/bunny_cdn_sdk/_client.py
    - src/bunny_cdn_sdk/_exceptions.py
  provides:
    - src/bunny_cdn_sdk/storage.py
  affects: []
tech_stack:
  added: []
  patterns:
    - HTTP Basic Auth via base64(zone_name:password) per RFC 7617
    - Hard-coded REGION_MAP dict for region-to-URL resolution
    - _build_url() helper strips leading slash to prevent double-slash URLs
    - upload() passes content= directly to httpx for streaming BinaryIO
key_files:
  created:
    - src/bunny_cdn_sdk/storage.py
  modified: []
decisions:
  - title: password stored as both api_key and instance attribute
    detail: >
      _BaseClient requires an api_key argument; passing password satisfies that
      contract and injects AccessKey header. StorageClient also stores password
      as self.password to construct the Basic Auth header on every request.
      Both headers are transmitted; Bunny Storage API uses the Basic Auth one.
  - title: ValueError on unknown region at construction time
    detail: >
      Plan allowed region lookup to be silent; raising ValueError immediately
      in __init__ surfaces misconfiguration early before any network call is made.
  - title: empty-body guard on upload response
    detail: >
      If the Storage API returns 204 with no body (possible on idempotent PUT),
      upload() returns {} rather than raising JSONDecodeError — consistent with
      CoreClient pattern from Plan 01.
metrics:
  duration: 81s
  completed_date: 2026-04-10
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
---

# Phase 03 Plan 02: StorageClient Summary

**One-liner:** StorageClient with 4 operations (upload, download, delete, list) using HTTP Basic Auth and a hard-coded 10-region REGION_MAP with HTTPS-only base URLs.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | StorageClient with region mapping, Basic Auth, upload/download/delete/list | e2714e4 | src/bunny_cdn_sdk/storage.py |

## What Was Built

`src/bunny_cdn_sdk/storage.py` — 172 lines implementing `StorageClient(_BaseClient)` with:

**Region mapping (STOR-05):**
- Module-level `REGION_MAP` dict covering all 10 regions: falkenstein, de, ny, la, sg, syd, uk, se, br, jh
- All base URLs use HTTPS (T-03-11 mitigation)
- Constructor validates region and raises `ValueError` immediately if unknown

**Authentication (T-03-07 mitigation):**
- `_build_auth_header()` encodes `base64(zone_name:password)` per RFC 7617
- All 4 operations pass this header explicitly in every `_sync_request` call

**upload() — STOR-01:**
- Signature: `upload(path: str, data: bytes | BinaryIO, content_type: str | None = None) -> dict`
- Passes `content=data` to httpx — file-like objects streamed without full memory buffer (T-03-09 mitigation)
- Optional `Content-Type` header support
- Returns `response.json()` or `{}` if body is empty

**download() — STOR-02:**
- Signature: `download(path: str) -> bytes`
- Returns `response.content` (raw bytes, not parsed JSON)

**delete() — STOR-03:**
- Signature: `delete(path: str) -> None`
- Returns nothing; response body not expected

**list() — STOR-04:**
- Signature: `list(path: str = "/") -> list[dict]`
- Returns `response.json()` — flat directory listing from Storage API

## Decisions Made

**1. Password stored as both api_key and self.password** — `_BaseClient` requires `api_key`; passing password satisfies the parent constructor and auto-injects `AccessKey`. `self.password` is retained to construct the Basic Auth header on each request. Both headers are sent; the Storage API validates via Basic Auth.

**2. ValueError on unknown region at construction time** — Raises immediately in `__init__` before any network activity, surfacing misconfiguration early.

**3. Empty-body guard on upload** — `response.json() if response.content else {}` prevents `JSONDecodeError` on 204 responses, matching the CoreClient pattern from Plan 01.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all 4 operations are fully implemented with correct HTTP methods, auth headers, URL construction, and return types.

## Threat Surface Review

No new network endpoints, auth paths, or trust boundaries beyond what the plan's threat model (T-03-07 through T-03-12) covers:
- T-03-07: Basic Auth encoded correctly per RFC 7617, validated by Bunny API
- T-03-08: `self.password` stored in instance (accepted, required for per-request auth)
- T-03-09: BinaryIO streamed via httpx `content=` parameter without memory buffering
- T-03-10: HTTPS-only base URLs enforce encrypted transport of zone credentials
- T-03-11: All REGION_MAP entries use `https://` prefix; httpx validates TLS by default
- T-03-12: No SDK-level audit logging; Bunny Storage API provides audit trail

## Self-Check

Verified:
- FOUND: src/bunny_cdn_sdk/storage.py (172 lines, exceeds min_lines: 150)
- FOUND: commit e2714e4

## Self-Check: PASSED
