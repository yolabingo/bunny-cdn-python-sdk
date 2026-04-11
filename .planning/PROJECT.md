# bunny-cdn-sdk

## What This Is

A thin, typed Python SDK wrapping the Bunny CDN REST APIs using `httpx`. Provides two service clients — Core and Storage — with a sync public API backed by async internals for concurrent batch operations. Configurable retry/backoff via `RetryTransport` or constructor kwargs. Designed for Python developers who need a clean, dependency-light interface to Bunny CDN without any magic.

## Core Value

A Python developer can `pip install bunny-cdn-sdk`, instantiate a client with their API key, and call methods that map 1:1 to Bunny CDN endpoints — no surprises, no hidden behavior.

## Current State — v1.1 Shipped (2026-04-10)

### Shipped in v1.1

- `RetryTransport` — composable `httpx.AsyncBaseTransport` with 429/5xx/network retry, exponential backoff + full jitter, Retry-After header support; 100% coverage
- `max_retries`/`backoff_base` constructor kwargs on `CoreClient`, `StorageClient`, `_BaseClient` — `max_retries=0` default preserves v1.0 behavior
- Coverage gaps closed: `BunnyAPIError.__str__` tested, `_pagination.py` at 100% (`list_single_page` removed), public surface smoke test added
- 98 tests, 99% total coverage (340 stmts, 2 miss)

### Shipped in v1.0 (foundation)

- `CoreClient` — 37 public methods across Pull Zones, Storage Zones, DNS Zones, Video Libraries, Utilities; concurrent batch via `asyncio.gather`; auto-paginating iterators
- `StorageClient` — upload, download, delete, list; 10-region HTTPS base-URL map; Basic Auth per RFC 7617
- `_BaseClient` — httpx.AsyncClient internals, `AccessKey` + `User-Agent` injection, HTTP-status → exception mapping, context manager support
- `_exceptions.py` — 8-class hierarchy (`BunnySDKError` → `BunnyAPIError` subtypes + `BunnyConnectionError` branch)
- `_pagination.py` — callback-based `pagination_iterator`; `PaginatedResponse` TypedDict

### Key Decisions (Validated)

| Decision | Outcome | Version |
|----------|---------|---------|
| Sync public API, async internals | Clean call site; `_gather()` enables concurrent batch | v1.0 |
| Plain dict returns | No Pydantic dependency; immune to API schema additions | v1.0 |
| Per-service clients | Matches Bunny's per-service auth model | v1.0 |
| `httpx` over `requests` | Async-first internals; sync+async in one library | v1.0 |
| `page=0` returns all items (no envelope) | Core API behavior handled correctly | v1.0 |
| `max_retries=0` default | Zero-config backward compat guaranteed | v1.1 |
| UserWarning (not ValueError) on client= + max_retries conflict | No surprise exceptions; warning is sufficient | v1.1 |
| `pragma: no cover` on unreachable post-loop sentinel | Correct 100% coverage without gaming metrics | v1.1 |
| `client=` keyword-only on CoreClient/StorageClient | Cleaner API; positional use was always ambiguous | v1.1 |

### Tech Debt Carried Forward

- `_client.py` lines 121-122 — bare `except Exception` on JSON parse failure in error extraction (needs malformed-body test)
- `test_public_surface.py` missing `RetryTransport` assertion
- 2 pre-existing `ty` errors in `storage.py` (`call-non-callable`, `invalid-type-form`)
- 59 pre-existing ruff violations (PLR2004, ANN401, TRY003)

## Next Milestone: v2.0 — Stream API

**Goal:** Add `StreamClient` covering the Stream API (Videos CRUD, Collections CRUD, pagination with camelCase envelope).

**Top candidates:**
- `StreamClient` — `list_videos`, `iter_videos`, `get_video`, `create_video`, `update_video`, `delete_video`; Collections CRUD
- `StreamClient.upload_video(video_id, data)` — stream video bytes
- Stream API pagination (`page`, `itemsPerPage` — camelCase envelope, different from Core)

*(Define fully via `/gsd-new-milestone`)*

## Requirements

### Validated

- ✓ All 29 v1.0 requirements satisfied — v1.0 ([archive](milestones/v1.0-REQUIREMENTS.md))
- ✓ QUAL-01: `BunnyAPIError.__str__` covered — v1.1
- ✓ QUAL-02: Context manager cleanup path covered (functional goal met; `_client.py` 93%, not 100%) — v1.1
- ✓ QUAL-03: `list_single_page()` removed from `_pagination.py` — v1.1
- ✓ QUAL-04: Public surface smoke test (`CoreClient`, `StorageClient`, `BunnyAPIError` from top-level) — v1.1
- ✓ RETRY-01: `from bunny_cdn_sdk import RetryTransport` — v1.1
- ✓ RETRY-02: Retry on 429/5xx/ConnectError/TimeoutException — v1.1
- ✓ RETRY-03: Exponential backoff with jitter; `max_retries`/`backoff_base` params — v1.1
- ✓ RETRY-04: Constructor kwargs; `max_retries=0` preserves v1.0 behavior — v1.1
- ✓ RETRY-05: `RetryTransport` independently composable — v1.1

### Active

*(None — awaiting v2.0 requirements definition via `/gsd-new-milestone`)*

### Out of Scope

| Feature | Reason |
|---------|--------|
| Response model objects (Pydantic/dataclass) | Plain dicts avoid dependency and schema-change brittleness |
| Webhook signature verification | Outside SDK scope |
| CLI tool | Not a goal for the SDK |
| Response caching | No magic |
| Automatic content-type detection for uploads | Caller responsibility |
| Unified client holding all API keys | Separate clients match Bunny's per-service auth model |
| `StreamClient` (Stream API) | Deferred to v2.0 |
| File upload progress callbacks | v2 candidate |
| Shield API, Edge Scripting API, Magic Containers | Deferred to future version |

## Context

Bunny CDN exposes three distinct API surfaces; v1.1 covers two:
- **Core** (`api.bunnycdn.com`) — account API key, covers management operations
- **Storage** (`{region}.storage.bunnycdn.com`) — storage zone password, per-zone
- **Stream** (`video.bunnycdn.com`) — deferred to v2.0

The sync-public/async-internal pattern gives callers a simple sync interface while enabling `asyncio.gather()` for batch operations internally — no async/await required at the call site. `RetryTransport` is composable — users can wire it manually or use constructor kwargs for zero-config retry.

## Constraints

- **Tech stack**: httpx only — no requests, aiohttp, or other HTTP libs
- **Python version**: 3.12+
- **Package manager**: `uv` — not pip directly; always run commands as `uv run <cmd>`
- **Type checker**: `ty` — not mypy or pyright
- **Return types**: plain `dict` from `response.json()` — no Pydantic, no dataclasses
- **Auth**: `AccessKey` header injection per-client — no credential sharing between clients
- **API fidelity**: method signatures match HLD exactly — no deviation without explicit decision

---

*Last updated: 2026-04-10 after v1.1 milestone*
