---
phase: 04-test-suite
plan: "03"
subsystem: storage-tests
tags: [testing, pytest, httpx, storage, mock-transport]
dependency_graph:
  requires: [04-01-test-infrastructure, 03-02-storage-client]
  provides: [storage-tests]
  affects: []
tech_stack:
  added: []
  patterns: [MockTransport-handler-injection, make_storage_client-fixture]
key_files:
  created:
    - tests/test_storage.py
  modified:
    - src/bunny_cdn_sdk/storage.py
    - src/bunny_cdn_sdk/_client.py
decisions:
  - "BinaryIO support requires reading into bytes before passing to httpx AsyncClient — sync file-like objects are not compatible with AsyncByteStream"
  - "headers must be popped from kwargs in _BaseClient._request before being passed as explicit kwarg to httpx.AsyncClient.request"
metrics:
  duration: "~2 minutes"
  completed: "2026-04-10"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 2
---

# Phase 4 Plan 03: StorageClient Tests Summary

**One-liner:** 9-test StorageClient suite with 100% storage.py line coverage, fixing two httpx async/headers bugs discovered during TDD execution.

## What Was Built

### tests/test_storage.py

9 flat test functions covering all StorageClient public methods and region validation:

| Test | Operation | Assertion |
|------|-----------|-----------|
| `test_upload_bytes_returns_empty_dict` | `upload(path, bytes)` | `result == {}` on 204 |
| `test_upload_binary_io_returns_empty_dict` | `upload(path, io.BytesIO(...))` | `result == {}` on 204 |
| `test_upload_with_content_type` | `upload(path, bytes, content_type=...)` | `result == {}`, no error |
| `test_download_returns_bytes` | `download(path)` | `isinstance(result, bytes)` and correct payload |
| `test_delete_returns_none` | `delete(path)` | `result is None` |
| `test_list_returns_list_of_dicts` | `list("/")` | `result == [{"ObjectName":...}]` |
| `test_region_falkenstein_base_url` | `StorageClient(region="falkenstein")` | `base_url == REGION_MAP["falkenstein"]` |
| `test_region_ny_base_url` | `StorageClient(region="ny")` | `base_url == REGION_MAP["ny"]` |
| `test_invalid_region_raises_value_error` | `StorageClient(region="invalid")` | `ValueError("Unknown region")` |

All tests use `make_storage_client(handler)` from `tests.conftest` for MockTransport injection. Region tests instantiate `StorageClient` directly (no HTTP call needed).

## pytest Output

```
collected 9 items

tests/test_storage.py::test_upload_bytes_returns_empty_dict PASSED
tests/test_storage.py::test_upload_binary_io_returns_empty_dict PASSED
tests/test_storage.py::test_upload_with_content_type PASSED
tests/test_storage.py::test_download_returns_bytes PASSED
tests/test_storage.py::test_delete_returns_none PASSED
tests/test_storage.py::test_list_returns_list_of_dicts PASSED
tests/test_storage.py::test_region_falkenstein_base_url PASSED
tests/test_storage.py::test_region_ny_base_url PASSED
tests/test_storage.py::test_invalid_region_raises_value_error PASSED

9 passed in 0.09s
```

## Coverage

```
Name                               Stmts   Miss  Cover
------------------------------------------------------
src/bunny_cdn_sdk/storage.py          43      0   100%
```

Full suite (58 tests across all 3 test modules):
```
src/bunny_cdn_sdk/__init__.py          3      0   100%
src/bunny_cdn_sdk/_client.py          57     10    82%
src/bunny_cdn_sdk/_exceptions.py      18      1    94%
src/bunny_cdn_sdk/_pagination.py      16      1    94%
src/bunny_cdn_sdk/_types.py            8      0   100%
src/bunny_cdn_sdk/core.py            137      0   100%
src/bunny_cdn_sdk/storage.py          43      0   100%
TOTAL                                282     12    96%
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed duplicate `headers` keyword argument in `_BaseClient._request()`**
- **Found during:** Task 1 (first test run)
- **Issue:** `_request()` built `headers` dict from `kwargs.get("headers", {})` then passed both `headers=headers` and `**kwargs` to `httpx.AsyncClient.request()`. Since `kwargs` still contained the `headers` key, httpx raised `TypeError: got multiple values for keyword argument 'headers'`.
- **Fix:** Changed `kwargs.get("headers", {})` to `kwargs.pop("headers", {})` so the key is removed from kwargs before the explicit `headers=headers` argument is passed.
- **Files modified:** `src/bunny_cdn_sdk/_client.py`
- **Commit:** 3a4e74d

**2. [Rule 1 - Bug] Fixed BinaryIO incompatibility with httpx AsyncClient**
- **Found during:** Task 1 (second test run, after fix 1)
- **Issue:** `storage.py` passed `content=data` directly to `_sync_request` where `data` could be an `io.BytesIO`. httpx `AsyncClient` requires an `AsyncByteStream`; passing a sync file-like object raised `RuntimeError: Attempted to send an sync request with an AsyncClient instance`.
- **Fix:** In `StorageClient.upload()`, read BinaryIO into bytes before passing: `payload = data.read() if hasattr(data, "read") else data`. This buffers the file content in memory (acceptable per SDK design — no streaming requirement at this scale).
- **Files modified:** `src/bunny_cdn_sdk/storage.py`
- **Commit:** 3a4e74d

## Known Stubs

None — all tests assert real behavior against MockTransport responses. No placeholder data.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. Test code only verifies existing `StorageClient` surface.

## Commits

- `3a4e74d` — feat(04-03): add StorageClient tests with 100% storage.py coverage

## Self-Check: PASSED
