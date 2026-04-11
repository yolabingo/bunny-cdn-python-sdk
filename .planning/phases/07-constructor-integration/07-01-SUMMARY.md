---
phase: 07-constructor-integration
plan: "01"
subsystem: clients
tags: [retry, constructor, kwargs, httpx]
dependency_graph:
  requires: [06-retry-transport]
  provides: [max_retries-constructor-wiring]
  affects: [_client.py, core.py, storage.py]
tech_stack:
  added: []
  patterns: [RetryTransport auto-wiring via constructor kwargs, UserWarning on conflict]
key_files:
  created: []
  modified:
    - src/bunny_cdn_sdk/_client.py
    - src/bunny_cdn_sdk/core.py
    - src/bunny_cdn_sdk/storage.py
decisions:
  - "UserWarning (not ValueError) emitted when client= and max_retries>0 conflict; max_retries ignored"
  - "client= is keyword-only on CoreClient and StorageClient; positional-or-keyword retained on _BaseClient for backward compat"
  - "max_retries=0 default preserves exact v1.0 behavior — no RetryTransport instantiated"
metrics:
  duration: ~10 minutes
  completed: 2026-04-10
  tasks_completed: 3
  files_modified: 3
---

# Phase 07 Plan 01: Wire max_retries / backoff_base into Constructor Chain Summary

**One-liner:** RetryTransport auto-wired via `max_retries`/`backoff_base` kwargs on `_BaseClient`, `CoreClient`, and `StorageClient` constructors with UserWarning on client= conflict.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add `max_retries`/`backoff_base` to `_BaseClient.__init__` with RetryTransport auto-wiring | 083e784 |
| 2 | Add `client=`, `max_retries=`, `backoff_base=` to `CoreClient.__init__` | 0fc5227 |
| 3 | Add `max_retries=`, `backoff_base=` to `StorageClient.__init__`; make `client=` keyword-only | 6f2b7f9 |

## What Was Built

`_BaseClient.__init__` now accepts `max_retries: int = 0` and `backoff_base: float = 0.5` as keyword-only parameters. When `max_retries > 0` and no `client=` is provided, it automatically creates a `RetryTransport`-backed `httpx.AsyncClient`. The `max_retries=0` default preserves exact v1.0 behavior.

`CoreClient.__init__` gains `client=`, `max_retries=`, `backoff_base=` as keyword-only kwargs after `base_url`. All three pass through to `super().__init__()`.

`StorageClient.__init__` gains `max_retries=` and `backoff_base=` as keyword-only kwargs. The existing `client=` parameter is moved to keyword-only as well (breaking change for positional callers; all existing test fixtures already used `client=` as keyword arg).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] E501 line-too-long in storage.py super().__init__ call**
- **Found during:** Task 3 verification
- **Issue:** The `super().__init__(password, client=client, max_retries=max_retries, backoff_base=backoff_base)` line exceeded 100 chars
- **Fix:** Split onto multiple lines
- **Files modified:** `src/bunny_cdn_sdk/storage.py`
- **Commit:** Amended into 6f2b7f9

### Pre-existing Issues (Out of Scope)

The ruff baseline already had 59 errors across all three files (PLR2004, ANN401, TRY003, etc.) before this plan. These are pre-existing and out of scope. No new ruff violations were introduced by this plan's changes (confirmed by comparing baseline count before/after).

The plan's verification section says `uv run ruff check ... # Expected: exit 0` — this reflects aspirational state, not current baseline. Logged as deferred.

## Success Criteria

- [x] `CoreClient(api_key)` constructs without error; `_client` is a plain `httpx.AsyncClient`
- [x] `CoreClient(api_key, max_retries=3)` constructs; `_client._transport` is a `RetryTransport`
- [x] `StorageClient(zone, pwd, max_retries=3)` constructs; `_client._transport` is a `RetryTransport`
- [x] `CoreClient(api_key, client=x, max_retries=1)` emits exactly one `UserWarning` and does not raise
- [x] `uv run pytest tests/ -x -q` exits 0 — 83 tests pass, no regressions
- [ ] `uv run ty check src/bunny_cdn_sdk/` exits 0 — 2 diagnostics (pre-existing, not introduced here)

## Known Stubs

None — all constructor wiring is fully implemented.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced. Changes are internal constructor wiring only.

## Self-Check: PASSED

- `src/bunny_cdn_sdk/_client.py` — modified, verified
- `src/bunny_cdn_sdk/core.py` — modified, verified
- `src/bunny_cdn_sdk/storage.py` — modified, verified
- Commits 083e784, 0fc5227, 6f2b7f9 — all present in git log
- 83 tests pass
