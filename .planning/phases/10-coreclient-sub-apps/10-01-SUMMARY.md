---
phase: 10-coreclient-sub-apps
plan: "01"
subsystem: cli
tags: [typer, rich, cli, pull-zone, storage-zone, CoreClient]

# Dependency graph
requires:
  - phase: 09-output-layer-error-handling
    provides: output_result(), sdk_errors(), console/err_console singletons, State dataclass
  - phase: 08-cli-scaffold
    provides: root Typer app, _app.py callback pattern, cli/__init__.py ImportError guard
provides:
  - pull_zone_app Typer sub-app with list/get/create/delete/purge/update commands
  - storage_zone_app Typer sub-app with list/get/create/delete/update commands
  - _pull_zone.py and _storage_zone.py modules ready for wiring into _app.py (Plan 04)
affects: [10-02-PLAN, 10-04-PLAN, 10-05-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Local imports of State and CoreClient inside each command function (avoids circular imports)"
    - "Auth guard pattern: check state.api_key before every command, exit 1 with actionable message"
    - "All SDK calls wrapped in sdk_errors() context manager"
    - "Alphabetical sort of iterator results before output_result() (D-10)"
    - "Update diff: fetch before/after, Table with only changed rows in red italic (D-12 to D-15)"

key-files:
  created:
    - src/bunny_cdn_sdk/cli/_pull_zone.py
    - src/bunny_cdn_sdk/cli/_storage_zone.py
  modified: []

key-decisions:
  - "Local imports of CoreClient and State inside command functions prevent circular import chains"
  - "update commands use --set KEY=VALUE parsed with split('=', 1); malformed pairs raise ValueError caught by sdk_errors()"
  - "Delete confirmation uses typer.confirm(abort=True) with --yes/-y bypass per D-01/D-02"

patterns-established:
  - "Command function local imports: from bunny_cdn_sdk.cli._app import State; from bunny_cdn_sdk.core import CoreClient"
  - "api_key guard before any SDK call with err_console.print() and raise typer.Exit(1)"
  - "output_result(data, columns=_COLUMNS, json_mode=state.json_output) — always pass explicit columns"

requirements-completed: [PZ-01, PZ-02, PZ-03, PZ-04, PZ-05, PZ-06, SZ-01, SZ-02, SZ-03, SZ-04, SZ-05]

# Metrics
duration: 2min
completed: 2026-04-11
---

# Phase 10 Plan 01: Pull Zone and Storage Zone CLI Sub-Apps Summary

**Two independent Typer sub-apps — pull_zone_app (6 commands) and storage_zone_app (5 commands) — with full CRUD, alphabetical list sorting, delete confirmation with --yes bypass, and update diff tables in red italic**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-11T15:24:12Z
- **Completed:** 2026-04-11T15:25:34Z
- **Tasks:** 2
- **Files modified:** 2 (created)

## Accomplishments

- `_pull_zone.py` with 6 commands: list (auto-paginating, sorted by Name), get, create, delete (confirm + --yes), purge, update (--set KEY=VALUE with before/after diff)
- `_storage_zone.py` with 5 commands following identical structural pattern, adapted for storage zones with `["Name", "Region", "Id"]` columns
- Both modules import cleanly with no circular imports; all 11 commands registered and spot-checked

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _pull_zone.py sub-app** - `1394d74` (feat)
2. **Task 2: Implement _storage_zone.py sub-app** - `4499784` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/bunny_cdn_sdk/cli/_pull_zone.py` - pull_zone_app with 6 commands implementing PZ-01 through PZ-06 and decisions D-01 to D-15
- `src/bunny_cdn_sdk/cli/_storage_zone.py` - storage_zone_app with 5 commands implementing SZ-01 through SZ-05 and decisions D-01 to D-15

## Decisions Made

- Local imports of `CoreClient` and `State` inside each command function body — prevents circular import because `_app.py` imports from `_output.py` which itself doesn't import sub-apps
- `--set` parsing uses `split("=", 1)` so values containing `=` are handled correctly; malformed pairs (no `=`) raise `ValueError` which `sdk_errors()` maps to exit 1 (T-10-01 mitigated)
- Delete commands fetch the resource first to get its name for the confirmation prompt and success message — one extra GET per delete (D-03/D-04)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None - both modules are fully wired with real CoreClient method calls. No hardcoded data or placeholder text.

## Threat Flags

No new threat surface beyond what the plan's threat model covers:
- T-10-01 (--set KEY=VALUE malformed input) — mitigated via `split("=", 1)` + ValueError
- T-10-03 (delete without confirmation) — mitigated via `typer.confirm(abort=True)` + `--yes` opt-out

## Next Phase Readiness

- `pull_zone_app` and `storage_zone_app` are standalone modules, not yet wired into `_app.py` — that happens in Plan 04 as specified
- Plan 02 (dns-zone sub-app) and Plan 03 (video-library sub-app) can proceed independently using the same patterns established here
- Plan 05 (test suite) has concrete targets: both files follow identical structure making test writing straightforward

## Self-Check: PASSED

- `/Users/toddj/github/bunny-cdn-python-sdk/main.git.create-sdk/src/bunny_cdn_sdk/cli/_pull_zone.py` — FOUND
- `/Users/toddj/github/bunny-cdn-python-sdk/main.git.create-sdk/src/bunny_cdn_sdk/cli/_storage_zone.py` — FOUND
- Commit `1394d74` — FOUND (feat(10-01): implement _pull_zone.py Typer sub-app)
- Commit `4499784` — FOUND (feat(10-01): implement _storage_zone.py Typer sub-app)

---
*Phase: 10-coreclient-sub-apps*
*Completed: 2026-04-11*
