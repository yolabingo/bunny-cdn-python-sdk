---
phase: 07-constructor-integration
plan: "02"
subsystem: tests
tags: [retry, constructor, integration-tests, httpx]
dependency_graph:
  requires: [07-01]
  provides: [RETRY-04-acceptance-tests]
  affects: [tests/test_constructor_retry.py]
tech_stack:
  added: []
  patterns: [MockTransport injection, RetryTransport._inner replacement, asyncio.sleep patching with AsyncMock]
key_files:
  created:
    - tests/test_constructor_retry.py
  modified: []
decisions:
  - "Used httpx._transport (private attr) instead of .transport — httpx.AsyncClient exposes no public .transport; plan had a typo"
metrics:
  duration: ~5 minutes
  completed: 2026-04-10
  tasks_completed: 2
  files_modified: 1
---

# Phase 07 Plan 02: Integration Tests for Constructor Retry Summary

**One-liner:** 15 integration tests covering CoreClient/StorageClient constructor retry wiring — call counts, backoff_base pass-through, UserWarning on conflict, and backward compatibility.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Create tests/test_constructor_retry.py with all 15 integration tests | d43a765 |
| 2 | Regression gate — full suite (98 tests) passes, _retry.py at 100% | (no commit needed — no code changes) |

## What Was Built

`tests/test_constructor_retry.py` with 15 tests organized into five groups:

- **Backward compatibility (2):** `max_retries=0` default produces exactly 1 HTTP call (v1.0 parity); no RetryTransport in transport chain.
- **CoreClient auto-wiring (4):** `max_retries=N` wires RetryTransport; always-500 with `max_retries=2` → 3 total calls; constructor path via `_inner` replacement; 1-fail handler → success on retry.
- **StorageClient auto-wiring (3):** `max_retries=N` wires RetryTransport; default no-retry; `max_retries=1` → 2 calls; `region=` + `max_retries=` together.
- **backoff_base pass-through (1):** `backoff_base=0.0` still retries but all sleep delays are 0.0.
- **UserWarning on conflict (4):** `client=` + `max_retries>0` emits exactly one UserWarning with correct message; no warning for `max_retries=0` or `client=` alone; StorageClient same behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan used `.transport` but httpx.AsyncClient exposes `._transport`**
- **Found during:** Task 1 first test run (8 of 15 tests failed with AttributeError)
- **Issue:** The plan's test code accessed `client._client.transport` — `httpx.AsyncClient` has no public `.transport` attribute; the internal attr is `._transport`
- **Fix:** Replaced all `._client.transport` references with `._client._transport` via `sed -i`
- **Files modified:** `tests/test_constructor_retry.py`
- **Commit:** d43a765 (included in the same task commit)

## Success Criteria

- [x] `uv run pytest tests/test_constructor_retry.py -v` exits 0 — 15 tests PASSED
- [x] `uv run pytest tests/test_core.py tests/test_storage.py -v` exits 0 (no regressions)
- [x] `uv run pytest tests/ -x -q` exits 0 — 98 tests pass
- [x] `_retry.py` coverage 100%
- [x] RETRY-04 acceptance: `CoreClient(api_key)` → 1 call; `CoreClient(api_key, max_retries=2)` → 3 calls

## Known Stubs

None — all tests are fully wired with real assertions.

## Threat Flags

None — test-only file; no new network endpoints, auth paths, or trust boundaries.

## Self-Check: PASSED

- `tests/test_constructor_retry.py` — created, verified
- Commit d43a765 — present in git log
- 98 tests pass (83 pre-existing + 15 new)
- `_retry.py` at 100% coverage
