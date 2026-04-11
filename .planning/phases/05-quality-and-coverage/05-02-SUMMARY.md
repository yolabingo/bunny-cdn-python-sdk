---
phase: "05"
plan: "02"
subsystem: tests, _pagination
tags: [coverage, context-manager, dead-code-removal, lifecycle-tests]
dependency_graph:
  requires: [05-01]
  provides: [_client.py-context-manager-coverage, _pagination.py-100-coverage]
  affects: [tests/test_client_lifecycle.py, src/bunny_cdn_sdk/_pagination.py]
tech_stack:
  added: []
  patterns: [asyncio.run-in-sync-test, context-manager-lifecycle-test]
key_files:
  created:
    - tests/test_client_lifecycle.py
  modified:
    - src/bunny_cdn_sdk/_pagination.py
decisions:
  - "Context manager lifecycle tests use asyncio.run() within a sync test function — no async test framework needed"
  - "list_single_page removed entirely (not deprecated) — zero callers confirmed in src/ and tests/"
metrics:
  duration: "1m 32s"
  completed: "2026-04-11T00:59:15Z"
  tasks_completed: 2
  files_changed: 2
---

# Phase 05 Plan 02: Context manager lifecycle tests + `list_single_page` cleanup Summary

**One-liner:** Context manager lifecycle tests cover `_client_owner=True` paths; dead `list_single_page` removed from `_pagination.py` to reach 100% coverage there.

## What Was Built

### Task 1: Context Manager Lifecycle Tests

Created `tests/test_client_lifecycle.py` with two tests:

- `test_async_context_manager_lifecycle` — uses `asyncio.run()` to exercise `__aenter__`/`__aexit__` with a `_BaseClient` created without an injected `client=` kwarg, forcing `_client_owner=True` and triggering `aclose()` in `__aexit__`
- `test_sync_context_manager_lifecycle` — exercises `__enter__`/`__exit__` with the same `_client_owner=True` setup

No `MockTransport` required — tests only validate enter/exit lifecycle with no HTTP requests.

**Coverage impact on `_client.py`:** Lines 48, 57–58, 62–63, 72 now covered. `_client.py` rose from 82% (10 miss) to 93% (4 miss).

### Task 2: Remove `list_single_page` from `_pagination.py`

- Removed `list_single_page` from `__all__` (line 10)
- Deleted the entire `list_single_page` function (lines 39–54)
- Confirmed zero callers in `src/` and `tests/` before removal

**Coverage impact on `_pagination.py`:** The one previously uncovered statement (line 54, the `return await fetch_page(page)` body) is eliminated along with the function. `_pagination.py` now has 14 stmts, 0 miss, 100%.

## Final Coverage

```
src/bunny_cdn_sdk/__init__.py     4 stmts,  0 miss, 100%
src/bunny_cdn_sdk/_client.py     57 stmts,  4 miss,  93%  (lines 121-122, 133, 135)
src/bunny_cdn_sdk/_exceptions.py 18 stmts,  0 miss, 100%
src/bunny_cdn_sdk/_pagination.py 14 stmts,  0 miss, 100%
src/bunny_cdn_sdk/_types.py       8 stmts,  0 miss, 100%
src/bunny_cdn_sdk/core.py       137 stmts,  0 miss, 100%
src/bunny_cdn_sdk/storage.py     43 stmts,  0 miss, 100%
TOTAL                           281 stmts,  4 miss,  99%
```

All 61 tests pass.

## Deviations from Plan

### Observed Gap — `_client.py` 93% not 100%

**Found during:** Task 1 verification
**Issue:** The plan expected `_client.py` to reach 100% after lifecycle tests. Lines 121–122, 133, 135 remain uncovered. These are:
- Line 121–122: `except Exception:` bare-except branch in JSON error-message extraction
- Line 133: `elif 500 <= status_code < 600:` server error branch
- Line 135: `raise BunnyServerError(...)` call

These lines were already in the 82%-coverage baseline (listed as misses before this plan). They are not context manager lifecycle paths — they require HTTP 5xx mock responses in `_request` tests. The plan's task scope was limited to context manager lifecycle, and these lines are pre-existing gaps outside that scope.

**Action taken:** None — these gaps are pre-existing, out of scope for this plan's two tasks, and require separate test coverage work. Documented here for tracking.

## Commits

| Hash | Message |
|------|---------|
| cc5bb27 | test(05-02): add context manager lifecycle tests for _BaseClient |
| 0e0e966 | refactor(05-02): remove dead list_single_page from _pagination.py |

## Known Stubs

None.

## Threat Flags

None — test-only additions and dead-code removal; no new network endpoints, auth paths, or schema changes.
