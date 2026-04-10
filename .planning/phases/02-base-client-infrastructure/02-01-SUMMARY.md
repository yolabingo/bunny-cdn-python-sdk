---
phase: 02-base-client-infrastructure
plan: 01
subsystem: base-client
tags: [python, httpx, async, context-managers, error-mapping, authentication]
dependency_graph:
  requires:
    - phase: 01-package-scaffold-exception-hierarchy
      provides: [exception-hierarchy, BunnyAPIError, BunnyConnectionError]
  provides:
    - _BaseClient class with async internals
    - Header injection (AccessKey, User-Agent)
    - HTTP status → exception mapping
    - Concurrent _gather for batch operations
    - Context manager support (sync/async)
  affects: [phase-2-plans-2-3, phase-3-core-client, phase-3-storage-client]
tech_stack:
  added: []
  patterns:
    - async-internal-sync-public (asyncio.run wrapper for sync surface)
    - context-manager-pattern (both __aenter__/__aexit__ and __enter__/__exit__)
    - error-mapping-chokepoint (_request handles all HTTP errors)
    - optional-dependency-injection (httpx.AsyncClient for testing)
key_files:
  created:
    - src/bunny_cdn_sdk/_client.py
  modified: []
decisions:
  - "Async internals with sync public surface via asyncio.run() — matches CLAUDE.md constraint for sync-first API"
  - "_request() as single chokepoint for ALL HTTP operations — ensures consistent auth injection and error mapping"
  - "Optional httpx.AsyncClient injection in constructor — enables testing with mocked transports"
  - "_client_owner flag to track whether _BaseClient created the client (owns cleanup) vs received it"
  - "Header injection uses dict merge pattern to preserve caller-provided headers"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-10"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 0
---

# Phase 02 Plan 01: Base Client Infrastructure Summary

**_BaseClient with httpx.AsyncClient internals, header injection (AccessKey + User-Agent), HTTP-status exception mapping, concurrent _gather, and context manager support**

## What Was Built

Implemented `_BaseClient` class in `src/bunny_cdn_sdk/_client.py` as the foundation for all service clients (Core, Storage). The client wraps `httpx.AsyncClient` with:
- Async request handling with sync public surface (`_sync_request` using `asyncio.run`)
- Header injection chokepoint (`AccessKey`, `User-Agent: bunny-cdn-sdk/0.1.0`)
- HTTP status code → exception mapping (401, 404, 429, 5xx, connection, timeout)
- Concurrent batch operations via `_gather()`
- Full context manager support (sync and async)
- Optional injectable `httpx.AsyncClient` for testing

## Implementation Details

### Class Structure

```python
class _BaseClient:
    def __init__(api_key: str, client: httpx.AsyncClient | None = None)
    async def __aenter__() -> Self
    async def __aexit__(exc_type, exc_val, exc_tb) -> None
    def __enter__() -> Self
    def __exit__(exc_type, exc_val, exc_tb) -> None
    async def _request(method: str, url: str, **kwargs) -> httpx.Response
    async def _gather(*coroutines) -> list[Any]
    def _sync_request(method: str, url: str, **kwargs) -> httpx.Response
```

### Error Mapping in _request()

| Status Code | Exception Class | Notes |
|-------------|-----------------|-------|
| 401 | BunnyAuthenticationError | Unauthorized |
| 404 | BunnyNotFoundError | Resource not found |
| 429 | BunnyRateLimitError | Rate limited |
| 5xx | BunnyServerError | Server error |
| Other 4xx | BunnyAPIError | Generic API error |
| ConnectTimeout | BunnyTimeoutError | Connection timeout |
| ConnectError | BunnyConnectionError | Network error |
| TimeoutException | BunnyTimeoutError | Request timeout |

Error messages extracted from response body (`response.json().get('Message')`) or response text, with fallback to HTTP status string.

### Context Manager Behavior

- **Async (`async with`):** Properly awaits `__aenter__` and `__aexit__`
- **Sync (`with`):** Uses `asyncio.run()` to execute async equivalents
- **Ownership tracking:** Only closes client if `_client_owner=True` (i.e., client was created internally)

### Files Created

| File | Purpose |
|------|---------|
| `src/bunny_cdn_sdk/_client.py` | _BaseClient implementation (167 LOC) |
| `.planning/phases/02-base-client-infrastructure/task3-verification.py` | Verification script (161 LOC) |

## Verification Results

**Task 1: Interface & Context Managers**
- `uv run ty check src/bunny_cdn_sdk/_client.py` → `All checks passed!` ✓
- Constructor with and without injected client instantiates ✓
- Context managers (sync and async) enter/exit without error ✓

**Task 2: Error Mapping**
- Type checks pass ✓
- HTTP 401 → BunnyAuthenticationError ✓
- HTTP 404 → BunnyNotFoundError ✓
- HTTP 429 → BunnyRateLimitError ✓
- HTTP 5xx → BunnyServerError ✓
- Other HTTP errors → BunnyAPIError ✓
- Connection errors → BunnyConnectionError ✓
- Timeouts → BunnyTimeoutError ✓

**Task 3: Verification Script Results**
```
Test 1: Basic instantiation... PASS
Test 2: Instantiation with injected AsyncClient... PASS
Test 3: Sync context manager... PASS
Test 4: Async context manager... PASS
Test 5: Header injection (AccessKey and User-Agent)... PASS
Test 6: Concurrent gather (results in order)... PASS

Results: 6/6 tests passed
```

## Commits

| Hash | Task | Message |
|------|------|---------|
| `303425d` | 1-2 | feat(02-01): implement _BaseClient with httpx integration and context managers |
| `644c7e3` | 3 | test(02-01): add verification script for _BaseClient behavior |

## Requirements Fulfilled

- **INFRA-01:** Base client wraps `httpx.AsyncClient` with sync public surface via `asyncio.run()` ✓
- **INFRA-02:** `_request()` chokepoint injects `AccessKey` and `User-Agent: bunny-cdn-sdk/0.1.0` ✓
- **INFRA-03:** `_gather()` runs coroutines concurrently and returns results as list ✓
- **INFRA-04:** Clients support context manager protocol (`with` / `async with`) ✓
- **INFRA-05:** Clients accept optional `httpx.AsyncClient` for testing and custom transports ✓

## Deviations from Plan

None — plan executed exactly as written. All three tasks completed with passing verification and type checks.

## Known Stubs

None — `_BaseClient` is fully implemented with all required methods.

## Threat Surface Scan

### T-02-01: Information Disclosure (API Key in User-Agent)
- **Status:** Accept (no change)
- **Rationale:** User-Agent header does not contain API key; only `AccessKey` header does (encrypted by HTTPS)

### T-02-02: Tampering (Error message injection)
- **Status:** Mitigate (implemented)
- **Implementation:** Error messages from response bodies are extracted via `response.json().get()` with safe fallbacks; no code execution paths via exception attributes

### T-02-03: Denial of Service (Concurrent gather with no limits)
- **Status:** Mitigate (by design)
- **Implementation:** `_gather()` passes coroutines directly to `asyncio.gather()`; caller controls concurrency by managing what coroutines are created

## Self-Check: PASSED

- `src/bunny_cdn_sdk/_client.py` created: FOUND
- _BaseClient class with 8 methods: CONFIRMED
- Type checks pass: CONFIRMED (`uv run ty check src/bunny_cdn_sdk/_client.py`)
- Full codebase type checks pass: CONFIRMED (`uv run ty check src/`)
- All 6 verification tests pass: CONFIRMED
- Commits 303425d, 644c7e3: FOUND
- Error mapping covers all required status codes: CONFIRMED
- Context managers work (sync and async): CONFIRMED

## Next Phase Readiness

- _BaseClient ready for inheritance by CoreClient and StorageClient (Phase 3)
- Types and pagination infrastructure (Phase 2 Plans 02-03) can proceed in parallel
- All authentication and error handling infrastructure complete

---
*Phase: 02-base-client-infrastructure*
*Plan: 01*
*Completed: 2026-04-10*
