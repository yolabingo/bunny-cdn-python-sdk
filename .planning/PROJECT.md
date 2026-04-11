# bunny-cdn-sdk

## What This Is

A thin, typed Python SDK wrapping the Bunny CDN REST APIs using `httpx`. Provides two service clients — Core and Storage — with a sync public API backed by async internals for concurrent batch operations. Designed for Python developers who need a clean, dependency-light interface to Bunny CDN without any magic.

## Core Value

A Python developer can `pip install bunny-cdn-sdk`, instantiate a client with their API key, and call methods that map 1:1 to Bunny CDN endpoints — no surprises, no hidden behavior.

## Current State — v1.0 Shipped (2026-04-10)

### Shipped

- `CoreClient` — 37 public methods across Pull Zones, Storage Zones, DNS Zones, Video Libraries, and Utilities; concurrent batch via `asyncio.gather`; auto-paginating iterators
- `StorageClient` — upload, download, delete, list; 10-region HTTPS base-URL map; Basic Auth per RFC 7617
- `_BaseClient` — httpx.AsyncClient internals, `AccessKey` + `User-Agent` injection, HTTP-status → exception mapping, context manager support
- `_exceptions.py` — 8-class hierarchy (`BunnySDKError` → `BunnyAPIError` subtypes + `BunnyConnectionError` branch)
- `_pagination.py` — callback-based `pagination_iterator`; `PaginatedResponse` TypedDict
- 58-test MockTransport suite — 96% total coverage; 100% on `core.py` and `storage.py`

### Key Decisions (Validated in v1.0)

| Decision | Outcome |
|----------|---------|
| Sync public API, async internals | Clean call site; `_gather()` enables concurrent batch without exposing async complexity |
| Plain dict returns | No Pydantic dependency; immune to API schema additions |
| Per-service clients | Matches Bunny's per-service auth model |
| `httpx` over `requests` | Async-first internals; sync+async in one library |
| `page=0` returns all items (no envelope) | Core API behavior handled correctly in pagination |
| Stream API deferred to v2 | Scope reduction — Core + Storage cover primary use cases |

### Tech Debt Carried Forward

- Context manager cleanup path untested (`_client.py` 82% coverage)
- `BunnyAPIError.__str__` untested (1 branch miss in `_exceptions.py`)
- `list_single_page()` exported but unused in `_pagination.py`
- No test exercises `from bunny_cdn_sdk import ...` public surface

## Next Milestone Goals — v2.0

*(To be defined via `/gsd-new-milestone`)*

Top candidates:
- `StreamClient` — Stream API (Videos CRUD, Collections CRUD, pagination with camelCase envelope)
- Public surface smoke tests — at least one test exercises `from bunny_cdn_sdk import CoreClient, StorageClient`
- v1.0 tech debt: context manager tests, `list_single_page` cleanup
- Retry / exponential backoff via custom httpx transport

## Requirements

### Validated in v1.0

All 29 v1 requirements satisfied. See [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md) for full archive.

### Active

*(None — awaiting v2.0 requirements definition)*

### Out of Scope

- `StreamClient` (Stream API) — deferred to v2.0
- Retry logic / exponential backoff — users can use custom httpx transports
- Response model objects (Pydantic/dataclass) — plain dicts avoid dependency and schema-change brittleness
- Rate limit handling / auto-retry on 429 — keep the client thin
- Webhook signature verification — out of scope
- CLI tool — not a goal for the SDK
- Response caching — thin wrapper, no magic
- Shield API, Edge Scripting, Magic Containers — deferred to future version
- File upload progress callbacks — v2 candidate
- Automatic content-type detection for uploads — caller responsibility
- Unified "Bunny" client holding all API keys — separate clients match Bunny's auth model

## Context

Bunny CDN exposes three distinct API surfaces; v1.0 covers two:
- **Core** (`api.bunnycdn.com`) — account API key, covers management operations
- **Storage** (`{region}.storage.bunnycdn.com`) — storage zone password, per-zone
- **Stream** (`video.bunnycdn.com`) — deferred to v2.0

The sync-public/async-internal pattern gives callers a simple sync interface while enabling `asyncio.gather()` for batch operations internally — no async/await required at the call site.

## Constraints

- **Tech stack**: httpx only — no requests, aiohttp, or other HTTP libs
- **Python version**: 3.12+
- **Package manager**: `uv` — not pip directly; always run commands as `uv run <cmd>`
- **Type checker**: `ty` — not mypy or pyright
- **Return types**: plain `dict` from `response.json()` — no Pydantic, no dataclasses
- **Auth**: `AccessKey` header injection per-client — no credential sharing between clients
- **API fidelity**: method signatures match HLD exactly — no deviation without explicit decision

---

*Last updated: 2026-04-10 — v1.0 milestone completion*
