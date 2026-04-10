# Phase 4: Test Suite - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate every exception path, every Core endpoint, and every Storage operation using `httpx.MockTransport` so the SDK ships with a complete, runnable test suite and no untested code paths.

**Three test modules:**
1. `tests/test_exceptions.py` — 6 exception types triggered by correct HTTP status/network conditions
2. `tests/test_core.py` — all 37 CoreClient methods (happy path minimum)
3. `tests/test_storage.py` — all 4 StorageClient operations including `bytes` and `BinaryIO` inputs

**Out of scope:** Integration tests against live Bunny CDN API, performance tests, load tests.
</domain>

<decisions>
## Implementation Decisions

### Test framework and tools
- **pytest** (already in dev dependencies via pyproject.toml)
- **httpx.MockTransport** for all HTTP mocking — this is the canonical approach for httpx-based SDKs; no `responses`, no `pytest-httpx` needed
- **pytest-cov** for coverage reporting (already in dev deps)

### Exception tests (test_exceptions.py)
- Test each of the 6 exception types by wiring a `MockTransport` that returns the triggering HTTP status or raises the network error
- Trigger conditions:
  - 401 → `BunnyAuthenticationError`
  - 404 → `BunnyNotFoundError`
  - 429 → `BunnyRateLimitError`
  - 5xx (500 sufficient) → `BunnyServerError`
  - `httpx.ConnectError` → `BunnyConnectionError`
  - `httpx.TimeoutException` → `BunnyTimeoutError`
- Each test: instantiate `CoreClient` with a `MockTransport` client, call any method, assert the correct exception type is raised

### Core client tests (test_core.py)
- Use `httpx.MockTransport` with a handler function that returns JSON responses
- Happy path only is required (per ROADMAP success criteria) — one test per public method
- Concurrent batch test: `get_pull_zones([1, 2])` — verify both IDs are fetched and returned in order
- Pagination test: `iter_pull_zones()` — mock two pages (`HasMoreItems: True` then `False`), verify all items yielded
- Test coverage target: 100% line coverage of `core.py`

### Storage client tests (test_storage.py)
- Use `httpx.MockTransport` similarly
- Upload: test with `bytes` payload AND `BinaryIO` payload (e.g., `io.BytesIO(b"data")`)
- Download: verify returns `bytes`
- Delete: verify returns `None`
- List: verify returns `list[dict]`
- Region mapping: verify at least 2 regions resolve to distinct URLs (instantiate with different regions, check `base_url`)
- Test coverage target: 100% line coverage of `storage.py`

### Test structure and conventions
- `tests/` directory at project root (not under `src/`)
- `tests/__init__.py` — empty file to make it a package
- `tests/conftest.py` — shared fixtures: `mock_client()` factory helper
- Tests use `pytest.raises` for exception assertions
- No test class hierarchy — flat functions with descriptive names (`test_get_pull_zone_returns_dict`)

### Coverage requirements
- 100% line coverage of `_exceptions.py`, `_client.py`, `core.py`, `storage.py`
- Run: `uv run pytest --cov=bunny_cdn_sdk --cov-report=term-missing`
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source files under test
- `src/bunny_cdn_sdk/_exceptions.py` — 8 exception classes to trigger
- `src/bunny_cdn_sdk/_client.py` — `_BaseClient._request()` chokepoint, `_gather()`
- `src/bunny_cdn_sdk/core.py` — 37 CoreClient methods
- `src/bunny_cdn_sdk/storage.py` — StorageClient with REGION_MAP

### Phase summaries (actual method signatures)
- `.planning/phases/03-core-and-storage-api-clients/03-01-SUMMARY.md` — CoreClient method list
- `.planning/phases/03-core-and-storage-api-clients/03-02-SUMMARY.md` — StorageClient details

### Requirements
- `.planning/REQUIREMENTS.md` TEST-01, TEST-02, TEST-03
- `.planning/ROADMAP.md` Phase 4 success criteria
- `CLAUDE.md` — `uv run pytest`, not plain pytest
</canonical_refs>

<specifics>
## Specific Ideas

- Use `httpx.MockTransport` with a `handler` callable pattern:
  ```python
  def handler(request):
      return httpx.Response(200, json={"Id": 1, "Name": "zone"})
  transport = httpx.MockTransport(handler)
  client = httpx.AsyncClient(transport=transport)
  core = CoreClient("api_key", client=client)
  ```
- For network errors: raise from handler with `raise httpx.ConnectError("Connection refused")`
- For timeouts: raise `httpx.TimeoutException("Timed out")`
</specifics>

<deferred>
## Deferred Ideas

- Integration tests against live API (v2 scope)
- Property-based tests with Hypothesis (v2 scope)
- Async test variants with `pytest-asyncio` (not needed — SDK exposes sync surface)
</deferred>

---

*Phase: 04-test-suite*
*Context gathered: 2026-04-10 from ROADMAP.md, REQUIREMENTS.md, and Phase 3 implementation*
