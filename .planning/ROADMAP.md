# Roadmap: bunny-cdn-sdk

**Granularity:** Coarse
**Total Phases:** 4
**Requirements covered:** 29/29

## Phase 1: Package Scaffold & Exception Hierarchy

**Goal:** Establish the installable package structure, typed exception hierarchy, and PEP 561 marker so all downstream phases build on a solid, importable foundation.

**Plans:** 2/2 plans complete

Plans:
- [x] 01-01-PLAN.md — Update Python 3.12 floor, create all 7 module stubs and py.typed marker
- [x] 01-02-PLAN.md — Implement full exception hierarchy in _exceptions.py

**Requirements:**
- INFRA-06, INFRA-09

**Success Criteria:**
- [ ] `uv sync` succeeds and `import bunny_cdn_sdk` works without errors
- [ ] `py.typed` is present in the installed package, satisfying `ty` PEP 561 discovery
- [ ] All 7 exception classes are importable and form the correct inheritance chain (`BunnyAuthenticationError` is a `BunnyAPIError` is a `BunnySDKError`)
- [ ] `BunnyAPIError` instances expose `status_code`, `message`, and `response` attributes

---

## Phase 2: Base Client Infrastructure

**Goal:** Deliver the `_BaseClient`, `_types.py`, `_pagination.py`, and `__init__.py` so the full internal machinery — auth injection, error mapping, concurrent gather, pagination, and context manager — is complete before any service client is written.

**Plans:**
1. Base client — implement `_client.py` with `httpx.AsyncClient` internals, `_request()` chokepoint (auth + User-Agent injection, HTTP-status → exception mapping), `_gather()` for concurrent batches, context manager support, and optional injectable transport
2. Types & pagination — implement `_types.py` (`PaginatedResponse` TypedDict) and `_pagination.py` (`list_*` single-page + `iter_*` auto-paginating iterator, decoupled via callback)
3. Public re-exports — implement `__init__.py` re-exporting `CoreClient`, `StorageClient`, and all exception classes

**Requirements:**
- INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-07, INFRA-08, INFRA-10

**Success Criteria:**
- [ ] `_BaseClient` can be instantiated with and without an injected `httpx.AsyncClient`; context manager (`with` / `__aenter__`) opens and closes the underlying client without error
- [ ] Every outbound request carries `AccessKey` and `User-Agent: bunny-cdn-sdk/{version}` headers (verifiable via `httpx.MockTransport`)
- [ ] `_gather([coro1, coro2])` returns results in input order and runs coroutines concurrently
- [ ] `iter_pull_zones()` yields individual items across multiple pages without the caller managing page numbers
- [ ] `from bunny_cdn_sdk import CoreClient, StorageClient, BunnyAPIError` resolves without `ImportError`

---

## Phase 3: Core API & Storage API Clients

**Goal:** Implement `CoreClient` (all Pull Zone, Storage Zone, DNS, Video Library, and utility endpoints) and `StorageClient` (upload, download, delete, list with 10-region URL mapping) so the SDK delivers its full v1 surface.

**Plans:** 2/2 plans complete

1. [x] 03-01-PLAN.md — Implement CoreClient with all 27+ methods across 5 resource groups
2. [ ] 03-02-PLAN.md — Implement StorageClient with upload, download, delete, list and 10-region URL mapping

**Requirements:**
- CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, CORE-06, CORE-07, CORE-08, CORE-09, CORE-10, CORE-11, STOR-01, STOR-02, STOR-03, STOR-04, STOR-05

**Success Criteria:**
- [ ] `CoreClient("key").list_pull_zones()` and all other CRUD methods return plain `dict` responses without raising on 2xx
- [ ] `CoreClient.get_pull_zones([id1, id2])` issues two requests concurrently (not sequentially) and returns both results
- [ ] `iter_pull_zones()` transparently fetches page 2 when page 1 `HasMoreItems` is true
- [ ] `StorageClient("zone", "password", region="ny")` uses `ny.storage.bunnycdn.com` as the base URL; all 10 regions resolve to distinct URLs
- [ ] `StorageClient.upload(path, data)` sends `bytes` and `BinaryIO` payloads without error

---

## Phase 4: Test Suite

**Goal:** Validate every exception path, every Core endpoint, and every Storage operation using `httpx.MockTransport` so the SDK ships with a complete, runnable test suite and no untested code paths.

**Plans:**
1. Exception tests — write `tests/test_exceptions.py` covering 401 → `BunnyAuthenticationError`, 404 → `BunnyNotFoundError`, 429 → `BunnyRateLimitError`, 5xx → `BunnyServerError`, network error → `BunnyConnectionError`, timeout → `BunnyTimeoutError`
2. Core client tests — write `tests/test_core.py` with mocked responses for all Pull Zone, Storage Zone, DNS, Video Library, and utility endpoints
3. Storage client tests — write `tests/test_storage.py` covering upload, download, delete, and list operations with mocked responses

**Requirements:**
- TEST-01, TEST-02, TEST-03

**Success Criteria:**
- [ ] `pytest` exits 0 with no failures or errors
- [ ] Each of the 6 exception types is triggered by the correct HTTP status/network condition in the test suite
- [ ] Every `CoreClient` method (all 27 endpoints) has at least one test covering the happy path
- [ ] All 4 `StorageClient` operations are tested with both `bytes` and `BinaryIO` inputs where applicable
- [ ] Test coverage report shows 100% line coverage of `_exceptions.py`, `_client.py`, `core.py`, and `storage.py`
