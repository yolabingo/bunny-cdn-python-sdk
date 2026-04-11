# bunny-cdn-sdk

## What This Is

A thin, typed Python SDK wrapping the Bunny CDN REST APIs using `httpx`. Provides two service clients — Core and Storage — with a sync public API backed by async internals for concurrent batch operations. Configurable retry/backoff via `RetryTransport` or constructor kwargs. Ships with an optional Typer-based CLI (`pip install bunny-cdn-sdk[cli]`) for managing Bunny CDN resources from the terminal. Designed for Python developers who need a clean, dependency-light interface to Bunny CDN without any magic.

## Core Value

A Python developer can `pip install bunny-cdn-sdk`, instantiate a client with their API key, and call methods that map 1:1 to Bunny CDN endpoints — no surprises, no hidden behavior.

## Current State — v2.0 Shipped (2026-04-11)

### Shipped in v2.0

- `bunnycdn` CLI — optional Typer + Rich CLI via `pip install bunny-cdn-sdk[cli]`; ImportError guard keeps SDK core lightweight for non-CLI users
- 5 sub-command groups: `pull-zone`, `storage-zone`, `dns-zone` (with nested `record` sub-commands), `video-library`, `storage`
- Auth: `--api-key`/`BUNNY_API_KEY` for Core; `--zone-name`/`--storage-key`/`--region` env vars for Storage
- Rich table output by default; `--json` flag for machine-readable output; all errors to stderr with exit 1
- `bunnycdn stats`, `bunnycdn billing`, `bunnycdn purge <url>` utility commands
- 241 tests total (110 CliRunner), 47/47 CLI requirements verified

<details>
<summary>v1.1 — Reliability & Coverage (shipped 2026-04-10)</summary>

- `RetryTransport` — composable `httpx.AsyncBaseTransport` with 429/5xx/network retry, exponential backoff + full jitter, Retry-After header support; 100% coverage
- `max_retries`/`backoff_base` constructor kwargs on `CoreClient`, `StorageClient`, `_BaseClient` — `max_retries=0` default preserves v1.0 behavior
- Coverage gaps closed: `BunnyAPIError.__str__` tested, `_pagination.py` at 100% (`list_single_page` removed), public surface smoke test added
- 98 tests, 99% total coverage (340 stmts, 2 miss)

</details>

<details>
<summary>v1.0 — MVP (shipped 2026-04-10)</summary>

- `CoreClient` — 37 public methods across Pull Zones, Storage Zones, DNS Zones, Video Libraries, Utilities; concurrent batch via `asyncio.gather`; auto-paginating iterators
- `StorageClient` — upload, download, delete, list; 10-region HTTPS base-URL map; Basic Auth per RFC 7617
- `_BaseClient` — httpx.AsyncClient internals, `AccessKey` + `User-Agent` injection, HTTP-status → exception mapping, context manager support
- `_exceptions.py` — 8-class hierarchy (`BunnySDKError` → `BunnyAPIError` subtypes + `BunnyConnectionError` branch)
- `_pagination.py` — callback-based `pagination_iterator`; `PaginatedResponse` TypedDict

</details>

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
| Entry point name `bunnycdn` (not `bunny`) | PyPI collision with file-watcher package | v2.0 |
| CLI deps in `[project.optional-dependencies]` (not `[dependency-groups]`) | Only former is pip-installable; correct packaging | v2.0 |
| `--set KEY=VALUE` style for update commands | Explicit, scriptable; consistent across all resource groups | v2.0 |
| DNS record sub-commands included (DZ-05/06/07) | Accepted complexity; full record lifecycle coverage | v2.0 |
| Local imports inside command functions | Avoids circular imports between cli/ modules | v2.0 |
| ImportError guard raises unconditionally in except branch | Prevents ty 'possibly-unresolved-reference' errors | v2.0 |
| asyncio.run + run_in_executor for stats concurrent calls | Avoids threading; matches existing SDK async patterns | v2.0 |

### Tech Debt Carried Forward

- `_client.py` lines 121-122 — bare `except Exception` on JSON parse failure in error extraction (needs malformed-body test)
- `test_public_surface.py` missing `RetryTransport` assertion
- 2 pre-existing `ty` errors in `storage.py` (`call-non-callable`, `invalid-type-form`)
- 59 pre-existing ruff violations (PLR2004, ANN401, TRY003)
- CLI Phase 08 VERIFICATION.md status `human_needed` — ImportError guard untested in clean venv (guard code correct; env constraint only)
- REQUIREMENTS.md traceability was never updated during v2.0 execution (checkboxes stayed `[ ]`); archived as-is

## Requirements

### Validated

- ✓ All 29 v1.0 requirements satisfied — v1.0 ([archive](milestones/v1.0-REQUIREMENTS.md))
- ✓ QUAL-01: `BunnyAPIError.__str__` covered — v1.1
- ✓ QUAL-02: Context manager cleanup path covered — v1.1
- ✓ QUAL-03: `list_single_page()` removed from `_pagination.py` — v1.1
- ✓ QUAL-04: Public surface smoke test — v1.1
- ✓ RETRY-01 through RETRY-05: RetryTransport implemented and composable — v1.1
- ✓ CLI-01 through CLI-04: CLI scaffold, entry point, ImportError guard — v2.0
- ✓ AUTH-01 through AUTH-04: Core and Storage auth via flags and env vars — v2.0
- ✓ OUT-01 through OUT-06: Rich tables, --json flag, stderr errors, exit codes — v2.0
- ✓ PZ-01 through PZ-06: Pull zone CRUD + update + purge — v2.0
- ✓ SZ-01 through SZ-05: Storage zone CRUD + update — v2.0
- ✓ DZ-01 through DZ-07: DNS zone CRUD + record add/update/delete — v2.0
- ✓ VL-01 through VL-05: Video library CRUD + update — v2.0
- ✓ ST-01 through ST-04: Storage file list/upload/download/delete — v2.0
- ✓ UTIL-01 through UTIL-03: purge URL, stats, billing — v2.0
- ✓ TEST-01 through TEST-03: CliRunner tests at SDK boundary, success+error+json paths — v2.0

### Active

- [ ] Release pipeline and version hygiene for v2.1 (see v2.1 requirements)

### Out of Scope

| Feature | Reason |
|---------|--------|
| Response model objects (Pydantic/dataclass) | Plain dicts avoid dependency and schema-change brittleness |
| Webhook signature verification | Outside SDK scope |
| Response caching | No magic |
| Automatic content-type detection for uploads | Caller responsibility |
| Unified client holding all API keys | Separate clients match Bunny's per-service auth model |
| `StreamClient` (Stream API) | Deferred to v3.0 |
| Shell autocomplete | Complexity not worth payoff in v2.0 |
| Recursive storage upload/download | Significant complexity; v3.0 candidate |
| Progress bars for upload | httpx sync doesn't expose upload progress callbacks |
| Config file (`bunnycdn.toml`) | Env vars sufficient for v2.0 |
| Interactive prompts for create/update fields | Unmaintainable at 37+ methods |
| `--output yaml` | Adds PyYAML dep; JSON + jq is the standard |
| Concurrent batch operations via CLI | SDK-direct use case, not CLI |

## Context

Bunny CDN exposes three distinct API surfaces; v2.0 covers two via both SDK and CLI:
- **Core** (`api.bunnycdn.com`) — account API key, covers management operations
- **Storage** (`{region}.storage.bunnycdn.com`) — storage zone password, per-zone
- **Stream** (`video.bunnycdn.com`) — deferred to v3.0

The sync-public/async-internal pattern gives callers a simple sync interface while enabling `asyncio.gather()` for batch operations internally. `RetryTransport` is composable — users can wire it manually or use constructor kwargs for zero-config retry. The CLI adds an optional Typer layer with no impact on library users who don't install `[cli]`.

**Current codebase:** 2,421 LOC src, 3,122 LOC tests, 241 total tests, Python 3.12+.

## Constraints

- **Tech stack**: httpx only — no requests, aiohttp, or other HTTP libs
- **Python version**: 3.12+
- **Package manager**: `uv` — not pip directly; always run commands as `uv run <cmd>`
- **Type checker**: `ty` — not mypy or pyright
- **Return types**: plain `dict` from `response.json()` — no Pydantic, no dataclasses
- **Auth**: `AccessKey` header injection per-client — no credential sharing between clients
- **API fidelity**: method signatures match HLD exactly — no deviation without explicit decision

## Current Milestone: v2.1 Release Engineering

**Goal:** Ship a production-ready release pipeline — CI, Dependabot, version hygiene, and TestPyPI publish.

**Target features:**
- Version management — pyproject.toml as single source, `bunnycdn.__version__` via importlib.metadata, CHANGELOG.md
- Local build verification — `uv build` produces valid wheel + sdist; twine check validates package metadata
- tox config — tox-uv plugin, isolated venv, py312 env; lint/typecheck as separate tox envs
- GHA CI workflow — runs tox envs on push/PR; Python 3.12
- Dependabot — pip ecosystem + GitHub Actions ecosystem
- Trusted Publishing (OIDC) — no stored tokens
- GHA release workflow — v* tag push auto-publishes + manual `workflow_dispatch` fallback
- TestPyPI publish + `pip install` smoke test
- Production PyPI workflow wired (trigger when ready)

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---

*Last updated: 2026-04-11 — Milestone v2.1 Release Engineering started*
