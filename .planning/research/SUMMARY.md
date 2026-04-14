# Project Research Summary

**Project:** bunny-cdn-sdk v2.0 — Optional Typer CLI
**Domain:** CLI wrapper around a REST SDK (CDN management)
**Researched:** 2026-04-10
**Confidence:** HIGH

## Executive Summary

Building a Typer CLI on top of the existing sync SDK is architecturally clean and low-risk because the SDK already wraps async internals behind a sync public API. Typer commands call SDK methods directly with no asyncio bridging needed — the impedance between Typer (synchronous) and the SDK (sync-public/async-internal) is zero. The recommended pattern is a `cli/` subpackage that is fully isolated from the SDK core: nothing in `bunny_cdn_sdk/__init__.py` or any non-CLI module ever imports from `cli/`, and an `ImportError` guard in `cli/__init__.py` ensures that base SDK users without `[cli]` extras get a clear message rather than a traceback.

Three decisions are final before any code is written and cannot be changed easily after publishing: (1) the entry point name must be `bunnycdn`, not `bunny` — a PyPI package named `bunny` (file watcher) creates a real collision risk; (2) the CLI optional dependencies belong in `[project.optional-dependencies]`, not `[dependency-groups]` — only the former gets published to PyPI and is pip-installable by end users; (3) the `StorageClient` requires three separate constructor arguments (`zone_name` + `password` + `region`), so the CLI must expose all three via flags or env vars (`BUNNY_STORAGE_ZONE`, `BUNNY_STORAGE_KEY`, `BUNNY_STORAGE_REGION`) with `region` defaulting to `"falkenstein"`.

The highest-complexity features are `update_*` commands (pull zone has ~30 configurable fields) and DNS record nested sub-commands (a third level of `app.add_typer` nesting). Both must be deferred. The `create_pull_zone` command should initially expose only required fields (`--name`, `--origin-url`). Everything else follows the same mechanical pattern: one file per resource group, `ctx.obj` `State` dataclass for auth, `sdk_errors()` context manager for exception handling, and `_output.py` for Rich/JSON rendering.

---

## Key Findings

### Recommended Stack

The v2.0 stack is additive only. The existing httpx/uv/Python 3.12+/ty foundation is unchanged. Two new runtime-optional dependencies are added under a `[cli]` extra: `typer>=0.12.0,<1` and `rich>=13.0.0`. The Typer 0.12 floor matters — it is the release that separated Rich as a peer dependency rather than bundling it. Rich 14.3.3 is already present in the project venv as a transitive dep of pip-audit tooling, so there is no version conflict risk; it simply needs to be declared as an explicit project dependency in `[project.optional-dependencies]`. Click is a transitive dep of Typer and must NOT be pinned directly in pyproject.toml.

**Core technologies:**
- `typer>=0.12.0,<1`: CLI framework — nested sub-apps, env var resolution, context propagation; 0.12 floor required for stable Rich peer dep model
- `rich>=13.0.0`: Terminal output — `Table`, `Console`, `Console(stderr=True)`; already in venv, needs explicit declaration
- `asyncio` (stdlib): No additional dep needed — SDK sync methods already wrap asyncio internally; never call `asyncio.run()` in CLI code
- `typer.testing.CliRunner`: Test harness — in-process CLI invocation, stdout/stderr capture, exit code inspection; included with Typer

**pyproject.toml pattern (critical decisions):**
```toml
[project.optional-dependencies]
cli = ["typer>=0.12.0,<1", "rich>=13.0.0"]

[project.scripts]
bunnycdn = "bunny_cdn_sdk.cli:app"
```

### Expected Features

The SDK exposes 37 CoreClient methods and 4 StorageClient methods. The CLI wraps a curated subset organized into 5 sub-apps plus root-level commands. Table stakes covers list/get on all 4 resource types, storage file operations, cache purge, and env var auth. Rich table output and `--json` flag are non-negotiable for scripting usability.

**Must have (table stakes):**
- `bunnycdn pull-zone list/get/purge` — primary CDN operations; proves the whole pattern
- `bunnycdn storage-zone list/get` — storage zone enumeration
- `bunnycdn dns-zone list/get` — DNS management entry point
- `bunnycdn video-library list/get` — video library entry point
- `bunnycdn storage list/upload/download/delete` — core file operations; requires separate StorageClient auth
- `bunnycdn purge <url>` — root-level command; URL-level cache invalidation
- `BUNNY_API_KEY` / `BUNNY_STORAGE_KEY` / `BUNNY_STORAGE_ZONE` env var auth
- `--json` flag on all commands — pipe-to-jq support
- Exit code 1+ on all errors — shell scripting requirement

**Should have (competitive):**
- `bunnycdn pull-zone create/delete` — full CRUD; `delete` needs `typer.confirm()` guard
- `bunnycdn storage-zone create/delete` and `bunnycdn dns-zone create/delete` — lifecycle management
- `bunnycdn video-library create/delete` — low complexity, rounds out CRUD
- `bunnycdn stats` and `bunnycdn billing` — operational dashboarding; low complexity
- Rich table output with curated columns per resource type (not all API fields)
- `--page`/`--per-page` flags on list commands for pagination control

**Defer to v3+:**
- `update_*` commands for all resources — flag surface explosion (~30 fields for pull zone); use SDK directly
- `bunnycdn dns-zone record add/update/delete` — nested sub-sub-commands; structural complexity
- `bunnycdn pull-zone hostname *` and `pull-zone block-ip *` — niche operations
- Recursive upload/download, shell autocompletion, `bunny.toml` config file

### Architecture Approach

The CLI is a thin, optional presentation layer organized as a `cli/` subpackage within `bunny_cdn_sdk/`. It never contains business logic. The package boundary is strict: no SDK module imports from `cli/`, the `ImportError` guard lives only in `cli/__init__.py` (with a `raise` in the except branch so `ty` sees unconditional successful import on the happy path), and sub-modules import Typer and Rich directly. Auth is resolved once per invocation in the root `@app.callback()` and stored in a typed `State` dataclass on `ctx.obj`. Client instantiation happens inside each command function to enable clean test mocking.

**Major components:**
1. `cli/__init__.py` — ImportError guard + re-exports `app`; hard isolation boundary between CLI and SDK core
2. `cli/_app.py` — root `typer.Typer(no_args_is_help=True)`; `@app.callback()` with `State` dataclass; `app.add_typer()` registrations
3. `cli/_output.py` — `sdk_errors()` context manager (7 exception types to exit codes 1-7); `output_result()` with `json.dumps(..., default=str)`; `_cell()` helper for None/dict/list coercion in table cells
4. `cli/pull_zone.py`, `cli/storage_zone.py`, `cli/dns_zone.py`, `cli/video_library.py` — CoreClient sub-apps; identical structural pattern
5. `cli/storage.py` — StorageClient sub-app; different auth wiring (`--zone-name`, `--storage-key`, `--region`)
6. `tests/cli/` — `CliRunner`-based tests; mock at SDK client boundary, never at HTTP boundary; assert content not ANSI formatting

**Data flow (happy path):**
```
bunnycdn pull-zone list
  -> cli/__init__.py ImportError guard
  -> Typer routes to pull_zone sub-app "list" command
  -> app.callback() -> State{api_key, storage_key} on ctx.obj
  -> list_pull_zones(ctx) -> CoreClient(api_key=state.api_key)
  -> client.list_pull_zones() -> plain dict
  -> output_result(dict, json_mode=False) -> Rich table to stdout
  -> exit 0

Error path: BunnyNotFoundError -> sdk_errors() -> typer.echo(err=True) -> raise typer.Exit(2)
```

### Critical Pitfalls

1. **Optional import isolation failure** — Any `import typer` at module scope reachable from `bunny_cdn_sdk/__init__.py` breaks `import bunny_cdn_sdk` for base users. The `cli/` subpackage is the hard boundary. Verify: `python -c "import bunny_cdn_sdk"` in a base-only venv must succeed.

2. **Entry point name collision** — `bunny` is an existing PyPI package (file watcher). The entry point must be `bunnycdn` in `pyproject.toml [project.scripts]`. This decision is final before publishing.

3. **Wrong pyproject.toml table for CLI deps** — `[dependency-groups]` is uv-local and not published to PyPI. CLI extras must be in `[project.optional-dependencies]`. Wrong table means `pip install 'bunny-cdn-sdk[cli]'` silently fails.

4. **`sys.exit()` instead of `raise typer.Exit()`** — `sys.exit(1)` produces unreliable exit codes in `CliRunner` tests. Always use `raise typer.Exit(code=N)` inside `sdk_errors()`. Every command body is wrapped in `with sdk_errors():`.

5. **StorageClient auth mismatch** — Constructor takes `zone_name` + `password` + `region` (three separate args). CLI must expose all three via env vars `BUNNY_STORAGE_ZONE` + `BUNNY_STORAGE_KEY` + `BUNNY_STORAGE_REGION` with `region` defaulting to `"falkenstein"`.

---

## Implications for Roadmap

### Phase 1: CLI Scaffold and Package Wiring
**Rationale:** pyproject.toml decisions (entry point name, optional dep table) are irreversible after publish. The `cli/` subpackage skeleton with its import guard and root app must exist before any command code is written. All subsequent phases build on this.
**Delivers:** `bunnycdn --help` works; `[cli]` extra installable via `pip install bunny-cdn-sdk[cli]`; base `import bunny_cdn_sdk` unaffected; `_app.py` with `State` dataclass and callback skeleton; `_output.py` stubs.
**Addresses:** Auth env var resolution (`BUNNY_API_KEY`, `BUNNY_STORAGE_KEY`, `BUNNY_STORAGE_ZONE`, `BUNNY_STORAGE_REGION`); `--json` flag in callback.
**Avoids:** Entry point collision (use `bunnycdn`), wrong pyproject.toml table, import isolation failure, lazy sub-app registration.

### Phase 2: Output Layer and Error Handling
**Rationale:** `_output.py` has no SDK dependency beyond `_exceptions.py`. It can be built and fully unit-tested before any sub-app exists. `sdk_errors()` is used by every command — it must be correct before any command code is written. `_cell()` prevents None/nested-dict crashes across all future table rendering.
**Delivers:** `sdk_errors()` covering all 7 `BunnySDKError` subclasses with correct exit codes 1-7; `output_result()` with Rich table path and `json.dumps(..., default=str)` JSON path; `_cell()` helper; `tests/cli/test_output.py` fully passing.
**Avoids:** `sys.exit()` anti-pattern, JSON `TypeError` on non-serializable values, Rich `TypeError` on None table cells.

### Phase 3: CoreClient Sub-Apps
**Rationale:** All four CoreClient sub-apps follow identical structure. Pull zone is built first because it has the most methods and proves the full end-to-end pattern (list with pagination, get by ID, create with required flags only, delete with confirmation, purge). Remaining three are mechanical repetition. DNS zone records are deferred.
**Delivers:** `bunnycdn pull-zone list/get/create/delete/purge`; `bunnycdn storage-zone list/get/create/delete`; `bunnycdn dns-zone list/get/create/delete` (flat only, no record sub-commands); `bunnycdn video-library list/get/create/delete`; `bunnycdn purge <url>`; full `tests/cli/test_pull_zone.py` etc. using `CliRunner` + `patch`.
**Avoids:** Module-level client instantiation, async anti-pattern, raw exception propagation, `update_*` scope creep.

### Phase 4: StorageClient Sub-App
**Rationale:** StorageClient has distinct auth wiring (`zone_name` + `password` + `region`) requiring separate treatment. Isolated to `cli/storage.py` with 4 commands. Built after CoreClient sub-apps so the pattern is established before handling the variation.
**Delivers:** `bunnycdn storage list [path]`, `bunnycdn storage upload <local> <remote>`, `bunnycdn storage download <remote> <local>`, `bunnycdn storage delete <path>`; all three StorageClient env vars wired; `tests/cli/test_storage.py`.
**Avoids:** StorageClient auth mismatch, missing `--zone-name` flag, incorrect region default.

### Phase 5: Utility Commands and Integration Hardening
**Rationale:** `bunnycdn stats` and `bunnycdn billing` are low-complexity and can be added last. Integration tests validate that sub-app registration, context propagation, and env var resolution work end-to-end across the full CLI tree.
**Delivers:** `bunnycdn stats [--pull-zone-id N] [--from DATE] [--to DATE]`; `bunnycdn billing`; integration test suite; CLI section in README.
**Avoids:** Missing `invoke_without_command=True` on root app, missing `--help` on sub-apps.

### Phase Ordering Rationale

- Phases 1 and 2 are strictly sequential and must complete before any command code: the entry point, import guard, `State` dataclass, and `sdk_errors()` context manager are dependencies of every subsequent file.
- Phases 3 and 4 can be parallelized if needed, but StorageClient's auth variation is easier to reason about after Phase 3's CoreClient pattern is reviewed.
- `update_*` commands are explicitly out of scope for v2.0: the flag-surface explosion problem (~30 optional fields for pull zone) has no clean CLI solution at this milestone. Document SDK direct use for updates.
- DNS record sub-sub-commands are out of scope for v2.0: three-level `app.add_typer` nesting is underdocumented for context propagation and needs a dedicated spike in a future milestone.

### Research Flags

All phases use well-documented, verified patterns. No phase requires `/gsd-research-phase`.

- **Phase 1:** Standard PEP 508 + Typer setup; entry point pattern verified in STACK.md.
- **Phase 2:** `contextmanager`, Rich `Table`, `Console` are stable stdlib/Rich APIs; full implementation detail in ARCHITECTURE.md.
- **Phase 3:** Mechanical repetition of the `app.add_typer` + `ctx.obj` + `sdk_errors()` pattern verified in ARCHITECTURE.md.
- **Phase 4:** StorageClient constructor verified from source; auth wiring pattern is the same as Phase 3 with different env var names.
- **Phase 5:** No novel patterns; stats/billing are simple CoreClient calls.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Rich 14.3.3 version verified from installed venv; Typer 0.12 floor from training data (Aug 2025); PEP 508 is spec |
| Features | HIGH | SDK method inventory read directly from `core.py` (37 methods) and `storage.py` (4 methods); StorageClient constructor verified |
| Architecture | HIGH | Typer `app.add_typer()`, `ctx.obj`, `@app.callback()` are stable APIs since Typer 0.4; ImportError guard is standard Python |
| Pitfalls | HIGH | Entry point collision verified (PyPI `bunny` exists); `[dependency-groups]` vs `[project.optional-dependencies]` is PEP spec; all other pitfalls grounded in Typer/Click/Rich source behavior |

**Overall confidence:** HIGH

### Gaps to Address

- **Typer exact current version:** Training cutoff Aug 2025. Verify with `uv add typer --dry-run` during Phase 1 and backfill pinned upper bound. The `>=0.12.0,<1` constraint is safe regardless.
- **`ty` type checker on optional import guard:** Pitfall 13 documents the risk of "possibly unresolved" errors. The fix (raise in except branch) is documented but must be verified with `uv run ty check src/` immediately after Phase 1 scaffold.
- **`update_*` flag strategy (future):** Deferred from v2.0. If a future milestone adds update commands, requires research on whether `--set KEY=VALUE` generic flags or explicit per-field flags is the right approach for 30+ optional fields.
- **DNS record nested sub-commands (future):** Three-level `app.add_typer` nesting with context propagation is underdocumented. Requires a spike in a future milestone.

---

## Sources

### Primary (HIGH confidence)
- `src/bunny_cdn_sdk/core.py` — 37 method inventory verified directly
- `src/bunny_cdn_sdk/storage.py` — 4 methods; `zone_name` + `password` + `region` constructor verified directly
- `src/bunny_cdn_sdk/_client.py` — `asyncio.run()` in `_sync_request` confirmed
- `pyproject.toml` — `[dependency-groups]` structure; ruff `select = ["ALL"]` confirmed
- `.venv/lib/.../rich-14.3.3.dist-info/METADATA` — Rich version and Python compatibility confirmed
- PEP 508 / PEP 735 — `[project.optional-dependencies]` vs `[dependency-groups]` distinction

### Secondary (MEDIUM confidence)
- Typer training data (Aug 2025 cutoff) — 0.12 breaking change (Rich as peer dep), `app.add_typer()`, `ctx.obj` patterns, CliRunner behavior
- PyPI `bunny` package — entry point collision; confirmed from training data

### Tertiary (LOW confidence)
- Typer exact current version — training cutoff Aug 2025; verify during Phase 1 implementation

---

*Research completed: 2026-04-10*
*Ready for roadmap: yes*
