# Phase 2: Base Client Infrastructure - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

## Phase Boundary

Deliver the `_BaseClient`, `_types.py`, `_pagination.py`, and `__init__.py` so the full internal machinery — auth injection, error mapping, concurrent gather, pagination, and context manager — is complete before any service client is written.

**Three distinct subsystems:**
1. **Base client** — `_client.py` with `httpx.AsyncClient` internals, `_request()` chokepoint (auth + User-Agent injection, HTTP-status → exception mapping), `_gather()` for concurrent batches, context manager support, and optional injectable transport
2. **Types & pagination** — `_types.py` (`PaginatedResponse` TypedDict) and `_pagination.py` (`list_*` single-page + `iter_*` auto-paginating iterator, decoupled via callback)
3. **Public re-exports** — `__init__.py` re-exporting `CoreClient`, `StorageClient`, and all exception classes

## Requirements Fulfilled

- **INFRA-01**: Base client wraps `httpx.AsyncClient` with sync public surface via `asyncio.run()`
- **INFRA-02**: `_request()` chokepoint injects `AccessKey` header and `User-Agent: bunny-cdn-sdk/{version}` on every call
- **INFRA-03**: `_gather()` runs multiple coroutines concurrently via `asyncio.gather()` and returns results as a list
- **INFRA-04**: Clients support context manager protocol (`with` statement)
- **INFRA-05**: Clients accept optional `httpx.AsyncClient` for testing and custom transports
- **INFRA-07**: `PaginatedResponse` TypedDict models Core API pagination envelope (`Items`, `CurrentPage`, `TotalItems`, `HasMoreItems`)
- **INFRA-08**: `list_*()` fetches a single page and returns the raw response; `iter_*()` lazily auto-fetches pages and yields individual items — pagination logic decoupled via callback
- **INFRA-10**: `__init__.py` re-exports `CoreClient`, `StorageClient`, and all exception classes

## Success Criteria

- [ ] `_BaseClient` can be instantiated with and without an injected `httpx.AsyncClient`; context manager (`with` / `__aenter__`) opens and closes the underlying client without error
- [ ] Every outbound request carries `AccessKey` and `User-Agent: bunny-cdn-sdk/{version}` headers (verifiable via `httpx.MockTransport`)
- [ ] `_gather([coro1, coro2])` returns results in input order and runs coroutines concurrently
- [ ] `iter_pull_zones()` yields individual items across multiple pages without the caller managing page numbers
- [ ] `from bunny_cdn_sdk import CoreClient, StorageClient, BunnyAPIError` resolves without `ImportError`

## Implementation Decisions

### Base Client (`_client.py`)

- **AsyncClient wrapping**: Use `httpx.AsyncClient` internally; expose sync methods via `asyncio.run()` for the public surface
- **Optional transport injection**: Accept `httpx.AsyncClient` in constructor for testing; create internal client if not provided
- **_request() chokepoint**: Single method that:
  - Injects `AccessKey` header (from client's `api_key` attribute)
  - Injects `User-Agent: bunny-cdn-sdk/{version}` header
  - Maps HTTP status codes to appropriate exceptions (via exception hierarchy from Phase 1)
  - Returns `response` object or raises exception
- **_gather() for batch operations**: Wraps `asyncio.gather(*coroutines)`, returns results as list in input order
- **Context manager support**: Implement `__aenter__` and `__aexit__` (async) and sync `__enter__`/`__exit__` that wrap the async equivalents

### Pagination (`_types.py`, `_pagination.py`)

- **PaginatedResponse TypedDict**: Define schema matching Bunny's Core API envelope:
  ```python
  PaginatedResponse = TypedDict('PaginatedResponse', {
      'Items': list,
      'CurrentPage': int,
      'TotalItems': int,
      'HasMoreItems': bool
  })
  ```
- **Pagination decoupling**: Provide a generic `pagination_iterator` callback that both `list_*()` and `iter_*()` use:
  - `list_*()` calls callback once for page 1, returns raw response
  - `iter_*()` calls callback repeatedly, yields individual items, auto-fetches on `HasMoreItems`
- **No endpoint-specific pagination logic**: Each Core/Storage endpoint that needs pagination will receive the callback, decoupling pagination from the business logic

### Public Re-exports (`__init__.py`)

- Re-export `CoreClient` and `StorageClient` (forward references to Phase 3 implementations, as empty stubs from Phase 1)
- Re-export all exception classes from `_exceptions.py`
- Keep re-exports in alphabetical order to satisfy ruff RUF022

## Canonical References

- `.planning/ROADMAP.md` — Phase 2 scope and success criteria
- `.planning/REQUIREMENTS.md` — INFRA-01 through INFRA-08, INFRA-10 definitions
- `src/bunny_cdn_sdk/_exceptions.py` — Exception hierarchy (completed in Phase 1)
- `CLAUDE.md` — Project constraints (uv, httpx-only, Python 3.12+, plain dict returns)

## Deferred Ideas

None — Phase 2 scope is fully defined by ROADMAP.md and requirements.

---

*Phase: 02-base-client-infrastructure*
*Context gathered: 2026-04-10 from ROADMAP.md and REQUIREMENTS.md*
