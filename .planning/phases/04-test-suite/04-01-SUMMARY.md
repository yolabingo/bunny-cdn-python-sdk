---
phase: 04-test-suite
plan: "01"
subsystem: test-infrastructure
tags: [testing, pytest, httpx, exceptions, mock-transport]
dependency_graph:
  requires: [01-02-exception-hierarchy, 03-01-core-client, 03-02-storage-client]
  provides: [test-infrastructure, exception-tests]
  affects: [04-02-core-tests, 04-03-storage-tests]
tech_stack:
  added: [pytest, pytest-cov, httpx.MockTransport]
  patterns: [MockTransport-handler-injection, _BaseClient-direct-testing]
key_files:
  created:
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_exceptions.py
  modified:
    - pyproject.toml
decisions:
  - "Use _BaseClient directly for exception tests; CoreClient does not accept client kwarg"
  - "Move --cov-fail-under=80 from addopts to poe test task to allow per-file test runs"
metrics:
  duration: "~2 minutes"
  completed: "2026-04-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 1
---

# Phase 4 Plan 01: Test Infrastructure + Exception Tests Summary

**One-liner:** MockTransport-based test infrastructure with 6 exception-mapping tests covering every SDK error type triggered by correct HTTP status or network condition.

## What Was Built

### tests/__init__.py
Empty package marker enabling pytest discovery of `tests/` as a Python package.

### tests/conftest.py
Two factory helpers shared across all test modules:
- `make_base_client(handler)` — injects `httpx.MockTransport` into `_BaseClient` via `httpx.AsyncClient(transport=...)`
- `make_storage_client(handler, region)` — same pattern for `StorageClient` which accepts the `client` kwarg directly

### tests/test_exceptions.py
6 tests confirming every exception class is triggered by the correct condition:

| Test | Trigger | Exception Raised |
|------|---------|-----------------|
| `test_authentication_error` | HTTP 401 | `BunnyAuthenticationError` |
| `test_not_found_error` | HTTP 404 | `BunnyNotFoundError` |
| `test_rate_limit_error` | HTTP 429 | `BunnyRateLimitError` |
| `test_server_error` | HTTP 500 | `BunnyServerError` |
| `test_connection_error` | `httpx.ConnectError` raised in handler | `BunnyConnectionError` |
| `test_timeout_error` | `httpx.TimeoutException` raised in handler | `BunnyTimeoutError` |

## pytest Output

```
collected 6 items

tests/test_exceptions.py::test_authentication_error PASSED               [ 16%]
tests/test_exceptions.py::test_not_found_error PASSED                    [ 33%]
tests/test_exceptions.py::test_rate_limit_error PASSED                   [ 50%]
tests/test_exceptions.py::test_server_error PASSED                       [ 66%]
tests/test_exceptions.py::test_connection_error PASSED                   [ 83%]
tests/test_exceptions.py::test_timeout_error PASSED                      [100%]

6 passed in 0.05s
```

Coverage: `_exceptions.py` 94%, `_client.py` 75% (exception-mapping branches all covered; uncovered lines are context manager methods and `_gather` — covered by subsequent plans).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Moved --cov-fail-under=80 from addopts to poe test task**
- **Found during:** Task 2 verification
- **Issue:** `pyproject.toml` `addopts` included `--cov-fail-under=80` which caused `uv run pytest tests/test_exceptions.py` to exit 1 (total coverage 27%) even though all 6 tests passed. Running individual test files during incremental phase development would always fail the coverage gate until all 3 test modules exist.
- **Fix:** Removed `--cov-fail-under=80` from `addopts`; moved it to the `poe test` task as `pytest --cov-fail-under=80`. Individual file runs now exit 0. Full `uv run poe test` still enforces 80% threshold.
- **Files modified:** `pyproject.toml`
- **Commit:** baf15c0

## Fixture Pattern

All test modules in phases 04-02 and 04-03 use the same pattern:

```python
from tests.conftest import make_base_client, make_storage_client

def test_something():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={...})
    client = make_base_client(handler)
    result = client._sync_request("GET", "https://api.bunnycdn.com/...")
```

No real HTTP requests are made. All transport is in-memory via `httpx.MockTransport`.

## Commits

- `a9d65b6` — feat(04-01): add test infrastructure (tests/__init__.py and conftest.py)
- `baf15c0` — feat(04-01): add 6 exception-mapping tests with pytest config fix

## Self-Check: PASSED
