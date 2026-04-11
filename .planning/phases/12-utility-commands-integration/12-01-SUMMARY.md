---
phase: 12-utility-commands-integration
plan: 01
subsystem: cli
tags: [typer, rich, asyncio, bunny-cdn, cli, statistics, billing]

# Dependency graph
requires:
  - phase: 10-coreclient-sub-apps
    provides: purge command pattern, State dataclass, sdk_errors() context manager, output_result()
  - phase: 11-storageclient-sub-app
    provides: test patterns for CliRunner mocking at CoreClient boundary
provides:
  - stats command on root app with per-zone concurrent statistics via asyncio.gather
  - billing command on root app with curated key-value billing display
  - _fmt_bytes() byte-formatting helper
  - _build_stats_row() statistics row construction helper
  - CliRunner tests for both commands (20 tests total)
affects: [12-02-README-cli-section, future-phases-using-stats-billing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.run(asyncio.gather(...)) for concurrent sync SDK calls from CLI command body"
    - "run_in_executor for calling sync SDK methods from within async gather"
    - "top-level @app.command functions registered directly on root app (same as purge)"

key-files:
  created:
    - tests/cli/test_stats.py
    - tests/cli/test_billing.py
  modified:
    - src/bunny_cdn_sdk/cli/_app.py

key-decisions:
  - "Used asyncio.run + loop.run_in_executor to call sync get_statistics() concurrently for all zones — avoids threading, matches existing SDK patterns"
  - "test_billing_shows_key_fields uses --json mode instead of table output to avoid Rich terminal truncation in CliRunner"
  - "_fmt_bytes(0) returns '0 B' — the zero case is handled by the n < 1024 branch since 0 < 1024"

patterns-established:
  - "asyncio.run + run_in_executor: wrap sync SDK calls in async gather from CLI commands"
  - "TDD Red-Green: failing tests committed before implementation for CLI commands"

requirements-completed: [UTIL-02, UTIL-03]

# Metrics
duration: 25min
completed: 2026-04-11
---

# Phase 12 Plan 01: Stats and Billing Commands Summary

**`bunnycdn stats` and `bunnycdn billing` top-level commands using concurrent asyncio.gather for per-zone statistics and curated billing key-value display**

## Performance

- **Duration:** 25 min
- **Started:** 2026-04-11T11:22:00Z
- **Completed:** 2026-04-11T11:47:00Z
- **Tasks:** 1 (TDD: RED + GREEN commits)
- **Files modified:** 3

## Accomplishments
- Added `_fmt_bytes()` helper converting byte counts to human-readable strings (B/KB/MB/GB)
- Added `_build_stats_row()` computing Name, RequestsServed, BandwidthUsed, BandwidthCached, CacheHitRate, Error% per zone
- Added `stats_cmd` on root app: lists all zones concurrently via `asyncio.gather` + `run_in_executor`, supports `--pull-zone-id`, `--from`, `--to` flags
- Added `billing_cmd` on root app: single `get_billing()` call with 8-column curated display
- 20 CliRunner tests covering success, error, --json, missing auth, date flags, error% computation, zero-requests edge case

## Task Commits

Each task was committed atomically with TDD commits:

1. **RED — Failing tests for stats and billing** - `a47d117` (test)
2. **GREEN — Implementation of stats and billing commands** - `69bdef7` (feat)

## Files Created/Modified
- `src/bunny_cdn_sdk/cli/_app.py` - Added `_fmt_bytes`, `_build_stats_row`, `stats_cmd`, `billing_cmd`, module-level `asyncio` and `datetime` imports
- `tests/cli/test_stats.py` - 12 tests: _fmt_bytes unit tests, success paths, date flags, error%, --json, missing auth, API error
- `tests/cli/test_billing.py` - 8 tests: success, key fields (--json), --json, missing auth, API error, call verification

## Decisions Made
- Used `asyncio.run(asyncio.gather(...))` with `loop.run_in_executor` to call the sync `CoreClient.get_statistics()` concurrently for all zones — avoids adding async SDK methods, keeps pattern consistent with existing CLI structure
- `test_billing_shows_key_fields` uses `--json` mode to verify column presence rather than table output, since CliRunner's narrow terminal causes Rich to truncate long column headers (e.g. "ThisMo…")
- `_fmt_bytes(0)` correctly returns "0 B" because `0 < 1024` — no special-case needed

## Deviations from Plan

None — plan executed exactly as written. The one test adjustment (using `--json` for key field verification) was correcting the test approach to handle Rich's terminal truncation behavior, not a deviation from the implementation spec.

## Issues Encountered
- Rich table truncates column headers in CliRunner's narrow terminal width — fixed `test_billing_shows_key_fields` to use `--json` mode which returns full field names in JSON keys rather than potentially truncated table headers

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `stats` and `billing` commands are complete and tested
- CLI is now feature-complete (purge + stats + billing + all sub-apps)
- Phase 12-02: README CLI section update is the remaining deliverable for v2.0 milestone

---
*Phase: 12-utility-commands-integration*
*Completed: 2026-04-11*
