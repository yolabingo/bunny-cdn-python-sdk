---
phase: 11-storageclient-sub-app
plan: "01"
subsystem: cli
tags: [typer, rich, storageclient, cli, storage]

requires:
  - phase: 10-coreclient-sub-apps
    provides: established sub-app pattern (deferred imports, auth guard, output_result), _app.py State dataclass with storage_key/zone_name/region fields
  - phase: 08-cli-scaffold
    provides: Typer app scaffold, State dataclass, _output.py sdk_errors/output_result

provides:
  - "storage_app Typer instance with list/upload/download/delete commands in src/bunny_cdn_sdk/cli/_storage.py"
  - "bunnycdn storage sub-command group wired into _app.py as name='storage'"

affects:
  - 11-storageclient-sub-app plan 02 (tests)
  - 12-utility-and-integration (integration verification)

tech-stack:
  added: []
  patterns:
    - "Deferred import pattern for State and StorageClient inside command function bodies (circular import prevention)"
    - "Auth guard checks state.zone_name and state.storage_key only (region always has default)"
    - "OSError re-raised as ValueError inside sdk_errors() context so file I/O errors use same stderr/exit-1 path"
    - "upload/download use typer.echo() for success; list uses output_result() with curated _COLUMNS"

key-files:
  created:
    - src/bunny_cdn_sdk/cli/_storage.py
  modified:
    - src/bunny_cdn_sdk/cli/_app.py

key-decisions:
  - "OSError from file writes wrapped as ValueError so sdk_errors() handles it — clean stderr + exit 1 without traceback"
  - "upload reads file as bytes (fh.read()) rather than passing BinaryIO handle — SDK calls .read() anyway; full-buffer appropriate for CLI scope"
  - "download overwrites local_path silently — consistent with Unix conventions (cp, curl -o)"
  - "StorageClient constructed as StorageClient(state.zone_name, state.storage_key, region=state.region) — positional for zone_name/password to match constructor signature"

patterns-established:
  - "Pattern: storage sub-app mirrors pull_zone_app pattern exactly — Typer(no_args_is_help=True), deferred imports, auth guard, sdk_errors() wrapping"
  - "Pattern: file I/O errors routed through ValueError into sdk_errors() for consistent CLI error presentation"

requirements-completed:
  - ST-01
  - ST-02
  - ST-03
  - ST-04

duration: 10min
completed: 2026-04-11
---

# Phase 11 Plan 01: StorageClient Sub-App Summary

**Typer storage sub-app with list/upload/download/delete commands wrapping StorageClient, wired into bunnycdn CLI as the `storage` sub-command group**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-11T00:00:00Z
- **Completed:** 2026-04-11
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `_storage.py` with four commands (list, upload, download, delete) following the established sub-app pattern from Phase 10
- All commands use deferred imports to prevent circular imports; auth guard checks zone_name and storage_key before any SDK call
- OSError from file writes is caught and re-raised as ValueError so sdk_errors() handles it cleanly (no raw tracebacks)
- Wired `storage_app` into `_app.py` with two lines (import + add_typer); `bunnycdn storage --help` shows all four commands
- All 110 existing CLI tests continue to pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _storage.py CLI sub-app (list/upload/download/delete)** - `8ee96f0` (feat)
2. **Task 2: Wire storage_app into _app.py** - `bb0081b` (feat)

## Files Created/Modified

- `src/bunny_cdn_sdk/cli/_storage.py` - New Typer sub-app with list/upload/download/delete commands wrapping StorageClient
- `src/bunny_cdn_sdk/cli/_app.py` - Added import of storage_app + app.add_typer(storage_app, name="storage")

## Decisions Made

- **OSError as ValueError:** File write errors in download and file-not-found in upload are converted to ValueError so sdk_errors() gives consistent stderr output and exit code 1 without a Python traceback.
- **fh.read() not BinaryIO:** Upload reads file into bytes before passing to StorageClient.upload() — SDK calls .read() internally anyway; bytes is simpler and sufficient for CLI use where progress bars are out of scope.
- **Silent overwrite on download:** No prompt if local_path exists — consistent with Unix conventions (cp, curl -o).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The `uv run python -m bunny_cdn_sdk.cli storage --help` command in the acceptance criteria fails (no `__main__` module), but `uv run bunnycdn storage --help` works correctly via the installed entry point. All acceptance criteria satisfied via equivalent commands.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `storage_app` is live and all four commands are registered
- Plan 02 (tests) can now write CliRunner tests against the storage sub-app
- No blockers or concerns

---
*Phase: 11-storageclient-sub-app*
*Completed: 2026-04-11*
