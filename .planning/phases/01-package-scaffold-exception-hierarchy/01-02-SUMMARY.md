---
phase: 01-package-scaffold-exception-hierarchy
plan: 02
subsystem: exception-hierarchy
tags: [python, exceptions, httpx, ruff, ty]
dependency_graph:
  requires: [01-01-installable-package]
  provides: [exception-hierarchy, bunny-api-error, bunny-connection-error]
  affects: [phase-2-client, phase-3-core, phase-3-storage]
tech_stack:
  added: []
  patterns: [type-checking-guard, pep563-deferred-annotations, explicit-__all__]
key_files:
  created: []
  modified:
    - src/bunny_cdn_sdk/_exceptions.py
decisions:
  - "TYPE_CHECKING guard for httpx.Response — avoids runtime httpx import in exceptions module, PEP 563 deferred annotations make it work as forward reference"
  - "__all__ sorted alphabetically to satisfy RUF022 (plan specified logical ordering; ruff requires sorted)"
  - "BunnyConnectionError is a sibling of BunnyAPIError under BunnySDKError — not a child (D-04)"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-10"
  tasks_completed: 1
  tasks_total: 1
  files_created: 0
  files_modified: 1
---

# Phase 01 Plan 02: Exception Hierarchy Summary

**One-liner:** Full 8-class exception hierarchy with BunnyAPIError carrying status_code/message/httpx.Response and a sibling BunnyConnectionError branch, passing ruff ALL and ty checks.

## What Was Built

Replaced the single-line docstring stub in `_exceptions.py` with the complete exception hierarchy required by Phase 2 (_client.py) and Phase 3 (core.py, storage.py).

### Files Modified

| File | Change |
|------|--------|
| `src/bunny_cdn_sdk/_exceptions.py` | Full implementation replacing stub docstring |

### Hierarchy Implemented

```
BunnySDKError (Exception)
├── BunnyAPIError              (status_code: int, message: str, response: httpx.Response)
│   ├── BunnyAuthenticationError   (401)
│   ├── BunnyNotFoundError         (404)
│   ├── BunnyRateLimitError        (429)
│   └── BunnyServerError           (5xx)
└── BunnyConnectionError       (network failure — no HTTP attributes)
    └── BunnyTimeoutError      (request timeout)
```

## Verification Results

1. `uv run ruff check src/bunny_cdn_sdk/_exceptions.py` → `All checks passed!` PASS
2. `uv run ty check src/bunny_cdn_sdk/_exceptions.py` → `All checks passed!` PASS
3. `grep -c 'class Bunny' src/bunny_cdn_sdk/_exceptions.py` → `8` PASS
4. `grep 'class BunnyConnectionError(BunnySDKError)'` → match (sibling branch confirmed) PASS
5. `grep 'httpx.Response'` → match (D-03 honored) PASS
6. Full assertion script → `All assertions passed` PASS

## Commits

| Hash | Message |
|------|---------|
| `aed0796` | feat(01-02): implement exception hierarchy in _exceptions.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Sorted __all__ to satisfy RUF022**
- **Found during:** Task 1 ruff check
- **Issue:** Plan specified logical/hierarchy ordering for `__all__`; ruff RUF022 requires isort-style alphabetical sort
- **Fix:** Reordered `__all__` entries alphabetically
- **Files modified:** `src/bunny_cdn_sdk/_exceptions.py`
- **Commit:** aed0796

## Known Stubs

None — `_exceptions.py` is fully implemented with all 8 classes.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes. The `response: httpx.Response` attribute on `BunnyAPIError` stores the server's response object in memory for the exception lifetime (T-02-03: accepted). The `__str__` surfaces API-sourced message strings (T-02-01: accepted, documented for Phase 4). No action required in this module.

## Self-Check: PASSED

- src/bunny_cdn_sdk/_exceptions.py modified: FOUND
- 8 Bunny classes present: CONFIRMED (grep -c returns 8)
- ruff exits 0: CONFIRMED
- ty exits 0: CONFIRMED
- All assertions passed: CONFIRMED
- Commit aed0796: FOUND
