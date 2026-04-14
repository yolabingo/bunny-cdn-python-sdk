---
phase: 14-tox-local-quality-gates
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 31
files_reviewed_list:
  - pyproject.toml
  - src/bunny_cdn_sdk/__init__.py
  - src/bunny_cdn_sdk/_client.py
  - src/bunny_cdn_sdk/_pagination.py
  - src/bunny_cdn_sdk/cli/__init__.py
  - src/bunny_cdn_sdk/cli/_app.py
  - src/bunny_cdn_sdk/cli/_dns_zone.py
  - src/bunny_cdn_sdk/cli/_output.py
  - src/bunny_cdn_sdk/cli/_pull_zone.py
  - src/bunny_cdn_sdk/cli/_storage_zone.py
  - src/bunny_cdn_sdk/cli/_storage.py
  - src/bunny_cdn_sdk/cli/_video_library.py
  - src/bunny_cdn_sdk/core.py
  - src/bunny_cdn_sdk/storage.py
  - tests/cli/conftest.py
  - tests/cli/test_app.py
  - tests/cli/test_billing.py
  - tests/cli/test_dns_zone.py
  - tests/cli/test_pull_zone.py
  - tests/cli/test_stats.py
  - tests/cli/test_storage_zone.py
  - tests/cli/test_storage.py
  - tests/cli/test_video_library.py
  - tests/conftest.py
  - tests/test_client_lifecycle.py
  - tests/test_constructor_retry.py
  - tests/test_core.py
  - tests/test_exceptions.py
  - tests/test_public_surface.py
  - tests/test_retry.py
  - tests/test_storage.py
  - tests/test_version.py
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-04-11T00:00:00Z
**Depth:** standard
**Files Reviewed:** 31
**Status:** issues_found

## Summary

The SDK is well-structured, with a clear separation between the base HTTP client, public API clients (Core and Storage), CLI layer, and test suite. Error handling, exception hierarchy, retry logic, and pagination are all correctly implemented. Auth injection is consistent. The `__version__` is correctly loaded from package metadata rather than a literal.

Four warnings require attention: a stale docstring referencing asyncio that no longer applies, an unchecked `KeyError` in `_pagination.py` on malformed API responses, a `CoreClient` created but never closed inside CLI commands (resource leak), and a `_sync_request` alias that adds noise without value. Five informational items are also noted.

## Warnings

### WR-01: Stale docstring references asyncio in CoreClient

**File:** `src/bunny_cdn_sdk/core.py:39-42`
**Issue:** The class-level docstring says `get_pull_zones([id1, id2, ...])` issues all requests concurrently via `asyncio.gather`. The implementation uses `ThreadPoolExecutor`, not asyncio. The note is misleading to callers.
**Fix:** Update the docstring:
```python
    Note on concurrent batch operations:
        ``get_pull_zones([id1, id2, ...])`` issues all requests concurrently via
        ``ThreadPoolExecutor``. For large ID lists, batch in chunks of 10-20 to stay
        within connection and rate limits.
```

### WR-02: pagination_iterator crashes with KeyError on malformed API response

**File:** `src/bunny_cdn_sdk/_pagination.py:34-36`
**Issue:** `response["Items"]` and `response["HasMoreItems"]` perform bare dict key access. If the Bunny CDN API returns a malformed response (missing keys, error object, or unexpected schema), this raises an unhandled `KeyError` that propagates to callers as a raw Python exception rather than a `BunnySDKError`. This is a correctness issue — the SDK contract says errors map to typed exceptions.
**Fix:**
```python
    items = response.get("Items")
    if items is None:
        msg = f"Paginated response missing 'Items' key: {list(response.keys())}"
        raise BunnySDKError(msg)
    yield from items
    if not response.get("HasMoreItems", False):
        break
```
Alternatively, document the assumption explicitly and add a test that covers malformed responses.

### WR-03: CoreClient opened inside CLI commands is never closed (resource leak)

**File:** `src/bunny_cdn_sdk/cli/_app.py:129`, `src/bunny_cdn_sdk/cli/_app.py:169`, `src/bunny_cdn_sdk/cli/_app.py:216` (also repeated in every CLI sub-app file)
**Issue:** Every CLI command creates a `CoreClient` (or `StorageClient`) without using it as a context manager or calling `.close()`. When `_client_owner=True` (which it is, because no `client=` is passed), the underlying `httpx.Client` is never explicitly closed. While CPython's reference counting typically handles this, it is not guaranteed by the Python data model and will cause resource warnings under `pytest -W error` or in PyPy.

Example in `_app.py`:
```python
        client = CoreClient(api_key=state.api_key)
        client.purge_url(url)
```
**Fix:** Use the context manager protocol so the client is always closed:
```python
        with CoreClient(api_key=state.api_key) as client:
            client.purge_url(url)
```
This pattern applies uniformly across all CLI command functions in `_app.py`, `_dns_zone.py`, `_pull_zone.py`, `_storage_zone.py`, `_storage.py`, and `_video_library.py`.

### WR-04: _sync_request is a no-op alias that adds call indirection without value

**File:** `src/bunny_cdn_sdk/_client.py:166-173`
**Issue:** `_sync_request` is documented as "kept for internal call-site compatibility" but all callers could use `_request` directly. The alias adds a call frame in every stack trace and implies a distinction that does not exist. More importantly, if a future maintainer adds behavior to `_request` (e.g., instrumentation), they may not realise `_sync_request` callers bypass it — or vice versa. This is a maintainability risk.
**Fix:** Remove `_sync_request` and update all call sites in `core.py` and `storage.py` to call `_request` directly, since the refactor away from async is complete. If backward compatibility with external code is needed, add a deprecation warning.

## Info

### IN-01: conftest.py variable named async_client is misleading

**File:** `tests/conftest.py:16-17`
**Issue:** The local variable created by `httpx.Client(transport=transport)` is named `async_client`, but `httpx.Client` is the synchronous client. The name `async_client` implies `httpx.AsyncClient` and will confuse readers.
**Fix:**
```python
    client = httpx.Client(transport=transport)
    return _BaseClient("test_api_key", client=client)
```

### IN-02: Same misleading variable name in make_storage_client

**File:** `tests/conftest.py:24-27`
**Issue:** The same `async_client` naming issue appears in `make_storage_client`.
**Fix:**
```python
    client = httpx.Client(transport=transport)
    return StorageClient("my-zone", "test_password", region=region, client=client)
```

### IN-03: test_retry.py docstring says AsyncHTTPTransport for a sync test

**File:** `tests/test_retry.py:328-329`
**Issue:** `test_composability_with_async_http_transport` documents itself as testing `RetryTransport(httpx.AsyncHTTPTransport())` but the test actually uses `httpx.MockTransport` (a sync transport) and `httpx.Client` (the sync client). The test name and docstring are misleading.
**Fix:** Rename to `test_composability_with_mock_transport` and update the docstring to accurately describe what is tested.

### IN-04: ThreadPoolExecutor with max_workers=0 when ids is empty

**File:** `src/bunny_cdn_sdk/core.py:180`
**Issue:** `get_pull_zones([])` calls `min(len(ids), 20)` where `len(ids)=0`, resulting in `ThreadPoolExecutor(max_workers=0)`. `ThreadPoolExecutor` raises `ValueError: max_workers must be greater than 0` in Python 3.12+.
**Fix:**
```python
        if not ids:
            return []
        with ThreadPoolExecutor(max_workers=min(len(ids), 20)) as pool:
            return list(pool.map(fetch_one, ids))
```
The same pattern exists in `_app.py:184` (`stats_cmd`) where `zones` could be empty.

### IN-05: _fmt_bytes does not handle negative input

**File:** `src/bunny_cdn_sdk/cli/_app.py:82-90`
**Issue:** `_fmt_bytes(n)` accepts `int` but has no guard against negative values. A negative `BandwidthUsed` value from a buggy API response would produce a string like `-500 B` rather than failing cleanly. This is low-risk but worth documenting or guarding.
**Fix:** Either document the precondition (`n >= 0`) or add:
```python
    if n < 0:
        return "—"
```

---

_Reviewed: 2026-04-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
