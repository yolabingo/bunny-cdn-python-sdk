---
phase: 06-retrytransport
plan: "01"
subsystem: transport
tags: [retry, httpx, transport, backoff, jitter]
dependency_graph:
  requires: []
  provides: [RetryTransport, _parse_retry_after]
  affects: [src/bunny_cdn_sdk/__init__.py]
tech_stack:
  added: []
  patterns: [composable-httpx-transport, exponential-backoff-with-jitter, sentinel-init-for-ty]
key_files:
  created:
    - src/bunny_cdn_sdk/_retry.py
  modified:
    - src/bunny_cdn_sdk/__init__.py
decisions:
  - Use module-level status code constants (_STATUS_TOO_MANY_REQUESTS, _STATUS_SERVER_ERROR_MIN/MAX) to satisfy PLR2004 instead of inline magic numbers
  - Use `from datetime import UTC, datetime` (UP017) instead of `timezone.utc`
  - Add `noqa: S311` on `random.uniform` call — jitter is not a cryptographic use case
  - Restructure try/except/else to move `return response` to else block (TRY300 compliance)
metrics:
  duration: ~10 minutes
  completed: 2026-04-11
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 06 Plan 01: Implement RetryTransport Summary

**One-liner:** Composable `httpx.AsyncBaseTransport` subclass with 429/5xx/network retry, exponential backoff + full jitter, and Retry-After header support.

## What Was Built

`src/bunny_cdn_sdk/_retry.py` — new module providing:

- `RetryTransport(httpx.AsyncBaseTransport)` — wraps any inner async transport, adds configurable retry loop (default `max_retries=3`, `backoff_base=0.5`)
- `_parse_retry_after(value: str) -> float` — RFC 7231 helper parsing both integer-seconds and HTTP-date Retry-After header formats; clamps to `>= 0.0`

`src/bunny_cdn_sdk/__init__.py` — updated to export `RetryTransport` in `__all__`, alphabetically between `CoreClient` and `StorageClient`.

## Tasks

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Create `src/bunny_cdn_sdk/_retry.py` | 054bf30 | `src/bunny_cdn_sdk/_retry.py` (created) |
| 2 | Export `RetryTransport` from `__init__.py` | 079257b | `src/bunny_cdn_sdk/__init__.py` (modified) |

## Verification Results

```
uv run ruff check src/bunny_cdn_sdk/_retry.py src/bunny_cdn_sdk/__init__.py  → All checks passed
uv run ty check src/bunny_cdn_sdk/_retry.py src/bunny_cdn_sdk/__init__.py   → All checks passed
from bunny_cdn_sdk import RetryTransport                                     → <class 'bunny_cdn_sdk._retry.RetryTransport'>
uv run pytest tests/ -x -q                                                   → 61 passed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff lint failures in plan-provided code**
- **Found during:** Task 1 verification
- **Issue:** The exact code in the plan triggered 7 ruff errors under the project's `select = ["ALL"]` ruleset:
  - `UP017` — `timezone.utc` → `datetime.UTC` alias required
  - `TRY300` — `return response` inside try block; must move to `else` block
  - `PLR2004` (x4) — magic values 429, 500, 600 in comparisons
  - `S311` — `random.uniform` flagged as non-cryptographic random
- **Fix:**
  - Replaced `from datetime import datetime, timezone` + `timezone.utc` with `from datetime import UTC, datetime` + `UTC`
  - Moved `return response` from inside `try` to the `else` clause of `try/except/else`
  - Extracted `_STATUS_TOO_MANY_REQUESTS = 429`, `_STATUS_SERVER_ERROR_MIN = 500`, `_STATUS_SERVER_ERROR_MAX = 600` as module-level constants
  - Added `# noqa: S311` on the `random.uniform` line (jitter is not a cryptographic operation)
- **Files modified:** `src/bunny_cdn_sdk/_retry.py`
- **Commit:** 054bf30

**2. [Out-of-scope] Pre-existing ty errors in `storage.py`**
- **Found during:** Overall verification (`uv run ty check src/bunny_cdn_sdk/`)
- **Issue:** Two pre-existing `ty` errors in `storage.py` (`call-non-callable` and `invalid-type-form`) surfaced when checking the whole package directory
- **Action:** Not fixed — pre-existing, out-of-scope per deviation scope boundary rules
- **Logged to:** Deferred items (pre-existing `storage.py` ty errors)

## Known Stubs

None — all logic is fully implemented. `_retry.py` has 32% test coverage because plan 06-02 provides the MockTransport-backed test suite.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. `RetryTransport` delegates unchanged `httpx.Request` objects to the inner transport; does not inspect, modify, or log headers.

## Self-Check: PASSED

- `src/bunny_cdn_sdk/_retry.py` — FOUND
- `src/bunny_cdn_sdk/__init__.py` — FOUND (modified)
- Commit 054bf30 — FOUND
- Commit 079257b — FOUND
- `from bunny_cdn_sdk import RetryTransport` — resolves to `bunny_cdn_sdk._retry.RetryTransport`
- `"RetryTransport" in bunny_cdn_sdk.__all__` — True
- 61 existing tests pass
