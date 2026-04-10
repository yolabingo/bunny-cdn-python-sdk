# bunny-cdn-sdk

## What This Is

A thin, typed Python SDK wrapping the Bunny CDN REST APIs using `httpx`. Provides two service clients — Core and Storage — with a sync public API backed by async internals for concurrent batch operations. Designed for Python developers who need a clean, dependency-light interface to Bunny CDN without any magic.

## Core Value

A Python developer can `pip install bunny-cdn-sdk`, instantiate a client with their API key, and call methods that map 1:1 to Bunny CDN endpoints — no surprises, no hidden behavior.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] `_BaseClient` — httpx.AsyncClient internals, sync public surface via `asyncio.run()`, `_request()` chokepoint with auth injection + error mapping, `_gather()` for concurrent batch operations, context manager support
- [ ] `_exceptions.py` — `BunnySDKError` hierarchy: `BunnyAPIError` (401 → `BunnyAuthenticationError`, 404 → `BunnyNotFoundError`, 429 → `BunnyRateLimitError`, 5xx → `BunnyServerError`), `BunnyConnectionError`, `BunnyTimeoutError`
- [ ] `_types.py` — `PaginatedResponse` TypedDict for Core (PascalCase) pagination envelope
- [ ] `_pagination.py` — `list_*()` single-page and `iter_*()` auto-paginating iterator patterns, decoupled via callback
- [ ] `CoreClient` — Pull Zones (CRUD + cache purge, hostname, blocked IP), Storage Zones (CRUD), DNS Zones (CRUD + records), Video Libraries (CRUD), Utilities (purge URL, statistics, countries, regions, billing)
- [ ] `StorageClient` — upload, download, delete, list with region-to-base-URL mapping (10 regions)
- [ ] `__init__.py` — public re-exports of CoreClient, StorageClient, and exception classes
- [ ] `py.typed` — PEP 561 marker for type-checking support
- [ ] Tests using `httpx.MockTransport` — full coverage of all clients and exception paths

### Out of Scope

- `StreamClient` (Stream API) — deferred to a future version
- Retry logic / exponential backoff — users can use custom httpx transports
- Response model objects (Pydantic/dataclass) — plain dicts avoid dependency and schema-change brittleness
- Rate limit handling / auto-retry on 429 — keep the client thin
- Webhook signature verification — out of v1 scope
- CLI tool — not a goal for the SDK
- Response caching — thin wrapper, no magic
- Shield API, Edge Scripting API, Magic Containers API — deferred to future version
- File upload progress callbacks — v2 candidate
- Automatic content-type detection for uploads — caller responsibility
- Unified "Bunny" client holding all API keys — separate clients match Bunny's auth model

## Context

Bunny CDN exposes three distinct API surfaces; v1 covers two:
- **Core** (`api.bunny.net`) — account API key, covers management operations
- **Storage** (`{region}.storage.bunnycdn.com`) — storage zone password, per-zone
- **Stream** (`video.bunnycdn.com`) — deferred to a future version

The Core API uses `page=0` to return all items without a pagination envelope, and `page>=1` for paginated responses. Storage has no pagination (flat directory listing).

The sync-public/async-internal pattern was chosen to give callers a simple sync interface while enabling `asyncio.gather()` for batch operations internally — no async/await required at the call site.

## Constraints

- **Tech stack**: httpx only — no requests, aiohttp, or other HTTP libs
- **Python version**: 3.10+ (union types, match statements if needed, modern asyncio)
- **Return types**: plain `dict` from `response.json()` — no Pydantic, no dataclasses
- **Auth**: `AccessKey` header injection per-client — no credential sharing between clients
- **API fidelity**: method signatures match HLD exactly — no deviation without explicit decision

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Sync public API, async internals | Users get simple sync calls; `_gather()` enables concurrent batch requests without exposing async complexity | — Pending |
| Plain dict returns | Avoids Pydantic dependency; caller decides how to use response data; immune to API schema additions | — Pending |
| Per-service clients (not one unified client) | Matches Bunny's auth model — each service has its own key type | — Pending |
| `httpx` over `requests` | Async-first internals require async HTTP; httpx is the standard choice for sync+async in one lib | — Pending |
| `page=0` behavior returns all items (no envelope) | Core API behavior — must handle both paginated and non-paginated response shapes | — Pending |
| Stream API deferred to v2 | Scope reduction — Core + Storage cover the primary use cases | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-10 after initialization*
