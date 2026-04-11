---
phase: 08-cli-scaffold
plan: 01
subsystem: cli
tags: [typer, rich, click, optional-extra, entry-point, importerror-guard]

# Dependency graph
requires: []
provides:
  - "[cli] optional extra in pyproject.toml with typer>=0.12.0 and rich>=13.0.0"
  - "bunnycdn entry point registered in [project.scripts]"
  - "src/bunny_cdn_sdk/cli/__init__.py with ImportError guard"
  - "src/bunny_cdn_sdk/cli/_app.py with root Typer app, State dataclass, @app.callback()"
  - "src/bunny_cdn_sdk/cli/_output.py with sdk_errors(), output_result(), _cell()"
  - "Auth options wired via BUNNY_API_KEY, BUNNY_STORAGE_KEY, BUNNY_STORAGE_ZONE, BUNNY_STORAGE_REGION env vars"
affects: [09-output-layer, 10-core-sub-apps, 11-storage-sub-app, 12-utility-integration]

# Tech tracking
tech-stack:
  added:
    - "typer 0.24.1 — CLI framework via [cli] optional extra"
    - "rich 14.3.3 — terminal output via [cli] optional extra"
    - "click 8.3.2 — transitive dep of typer"
  patterns:
    - "ImportError guard with unconditional raise in except branch — prevents ty 'possibly-unresolved-reference' errors"
    - "State dataclass on ctx.obj — typed auth carrier propagated to all sub-commands"
    - "sdk_errors() context manager — maps all SDK exceptions to stderr + Exit(1)"
    - "cast('State', ctx.obj) — ty-safe access to ctx.obj typed as Any in Typer stubs"

key-files:
  created:
    - src/bunny_cdn_sdk/cli/__init__.py
    - src/bunny_cdn_sdk/cli/_app.py
    - src/bunny_cdn_sdk/cli/_output.py
  modified:
    - pyproject.toml

key-decisions:
  - "FBT003 added to cli per-file-ignores — typer.Option(False, '--json') is positional bool, ruff FBT003 fires; suppressed globally for cli/ to match FBT001/FBT002"
  - "Generator moved to TYPE_CHECKING block in _output.py — ruff TC003 requires stdlib annotation-only imports under TYPE_CHECKING when from __future__ import annotations is present"
  - "cast('State', ctx.obj) used instead of state: State = ctx.obj — ty cannot infer ctx.obj type (it's Any in Typer stubs)"
  - "EM101 fixed by extracting _MSG variable before try/except in __init__.py — ruff forbids string literals in raise"

patterns-established:
  - "Pattern: cli/ subpackage isolation — nothing in src/bunny_cdn_sdk/__init__.py imports from cli/"
  - "Pattern: ImportError guard raises unconditionally — no _CLI_AVAILABLE flag antipattern"
  - "Pattern: All per-command auth checks are deferred to Phase 10 — scaffold only wires State, does not enforce non-empty keys"

requirements-completed: [CLI-01, CLI-02, CLI-03, CLI-04, AUTH-01, AUTH-02, AUTH-03]

# Metrics
duration: 35min
completed: 2026-04-10
---

# Phase 08 Plan 01: CLI Scaffold Summary

**Typer 0.24.1 + Rich 14.3.3 CLI scaffold wired as [cli] optional extra with bunnycdn entry point, ImportError guard, typed State dataclass, and sdk_errors() exception context manager**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-04-10
- **Completed:** 2026-04-10
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `pip install bunny-cdn-sdk[cli]` installs typer 0.24.1 + rich 14.3.3; `bunnycdn --help` shows full auth option table
- Import isolation confirmed: `import bunny_cdn_sdk` completes without touching Typer/Rich; cli/ is never reached from SDK import chain
- All 5 auth options wired via env vars (BUNNY_API_KEY, BUNNY_STORAGE_KEY, BUNNY_STORAGE_ZONE, BUNNY_STORAGE_REGION) and --flag equivalents
- 98 pre-existing tests pass unaffected; ty shows only the 2 pre-existing storage.py errors (baseline preserved)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire pyproject.toml — [cli] extra, entry point, ruff ignore** - `6585f81` (chore)
2. **Task 2: Create cli/ subpackage — __init__.py, _app.py, _output.py** - `3431f5c` (feat)

## Files Created/Modified

- `pyproject.toml` — Added [project.optional-dependencies] cli section, [project.scripts] bunnycdn entry, ruff per-file-ignores for cli/ (TRY003, FBT001, FBT002, FBT003, PLR0913)
- `src/bunny_cdn_sdk/cli/__init__.py` — ImportError guard with unconditional raise + app re-export
- `src/bunny_cdn_sdk/cli/_app.py` — Root Typer app, State dataclass, @app.callback() with all auth options
- `src/bunny_cdn_sdk/cli/_output.py` — sdk_errors() context manager mapping all BunnySDKError subclasses to Exit(1), output_result(), _cell()

## Decisions Made

- **FBT003 added to per-file-ignores:** `typer.Option(False, "--json", ...)` uses a boolean positional value (FBT003); per-file-ignore keeps the call site clean and consistent with the Typer API
- **Generator under TYPE_CHECKING:** ruff TC003 requires annotation-only imports in TYPE_CHECKING block when `from __future__ import annotations` is active; moved `collections.abc.Generator` there
- **cast("State", ctx.obj):** `ctx.obj` is typed `Any` in Typer stubs; direct assignment `state: State = ctx.obj` does not satisfy `ty`'s possibly-unresolved-reference rule; string-form cast is ty-safe
- **EM101 fix via _MSG variable:** ruff EM101 forbids string literals directly in `raise` statements; extracted error message to `_MSG` constant before the try block

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff EM101: string literal in raise**
- **Found during:** Task 2 (_output.py initial write)
- **Issue:** `raise ImportError("long message")` violates ruff EM101; ruff EM is not in per-file-ignores for cli/
- **Fix:** Extracted message to `_MSG = (...)` constant before the try/except block
- **Files modified:** src/bunny_cdn_sdk/cli/__init__.py
- **Verification:** `uv run ruff check src/bunny_cdn_sdk/cli/` exits 0
- **Committed in:** 3431f5c (Task 2 commit)

**2. [Rule 1 - Bug] ruff TC003: Generator import not in TYPE_CHECKING block**
- **Found during:** Task 2 (_output.py initial write)
- **Issue:** `from collections.abc import Generator` used only in annotations; ruff TC003 requires it under TYPE_CHECKING when `from __future__ import annotations` is present
- **Fix:** Moved import under `if TYPE_CHECKING:` block
- **Files modified:** src/bunny_cdn_sdk/cli/_output.py
- **Verification:** `uv run ruff check src/bunny_cdn_sdk/cli/` exits 0
- **Committed in:** 3431f5c (Task 2 commit)

**3. [Rule 1 - Bug] ty no-matching-overload on typer.Option with param_decls= keyword**
- **Found during:** Task 2 (_app.py, attempting keyword form for --json option)
- **Issue:** `typer.Option(param_decls=["--json"])` fails ty overload resolution — Typer's Option takes `*param_decls` positionally, not as a keyword argument
- **Fix:** Reverted to positional form `typer.Option(False, "--json", ...)` and added FBT003 to pyproject.toml per-file-ignores
- **Files modified:** src/bunny_cdn_sdk/cli/_app.py, pyproject.toml
- **Verification:** `uv run ty check src/` shows only 2 pre-existing storage.py errors
- **Committed in:** 3431f5c (Task 2 commit)

**4. [Rule 1 - Bug] Redundant noqa directives removed**
- **Found during:** Task 2 (ruff check iterations)
- **Issue:** `# noqa: PLR0913` and `# noqa: FBT001` inline on def/param lines were flagged as unused (RUF100) since those rules are already suppressed in per-file-ignores
- **Fix:** Removed inline noqa comments; per-file-ignores cover the rules globally for cli/
- **Files modified:** src/bunny_cdn_sdk/cli/_app.py
- **Verification:** `uv run ruff check src/bunny_cdn_sdk/cli/` exits 0
- **Committed in:** 3431f5c (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (all Rule 1 - ruff/ty lint corrections)
**Impact on plan:** All fixes were lint/type correctness issues discovered during mandatory post-write checks. No scope changes. Plan logic and contracts are unchanged.

## Issues Encountered

- ruff `E402` (module import not at top) fired on `from bunny_cdn_sdk.cli._app import app` in `__init__.py` after extracting `_MSG` before the try block — resolved by restoring the `# noqa: E402` comment on that import line

## Known Stubs

- `output_result()` in `_output.py`: non-JSON path calls `typer.echo(str(data))` as a placeholder — full Rich table rendering is deferred to Phase 09. This is intentional and documented in the code comment. Phase 09 will replace this line.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 09 (Output Layer): `output_result()` and `_cell()` in `_output.py` are the extension points; Phase 09 replaces the `typer.echo(str(data))` stub with Rich table rendering
- Phase 10 (CoreClient Sub-Apps): Import `app` from `bunny_cdn_sdk.cli._app`, call `app.add_typer(sub_app)`, access auth via `cast("State", ctx.obj).api_key`
- Phase 11 (StorageClient Sub-App): Same pattern; use `state.storage_key`, `state.zone_name`, `state.region` for StorageClient constructor
- No blockers — scaffold passes ty, ruff, and all 98 existing tests

---
*Phase: 08-cli-scaffold*
*Completed: 2026-04-10*
