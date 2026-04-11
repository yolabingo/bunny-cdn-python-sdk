---
phase: 09-output-layer-error-handling
plan: "01"
subsystem: cli
tags: [output, rich, table, cli]
dependency_graph:
  requires: [08-cli-scaffold]
  provides: [output_result-with-columns, rich-table-rendering]
  affects: [phase-10-coreclient-sub-apps]
tech_stack:
  added: []
  patterns: [rich-table-rendering, capsys-capture]
key_files:
  created: []
  modified:
    - src/bunny_cdn_sdk/cli/_output.py
    - tests/cli/test_app.py
decisions:
  - "Rich Table rendered via existing console singleton (stdout); capsys captures plain text in non-TTY pytest environment"
  - "isinstance(data, dict) wraps single dict in list for unified rendering code path"
  - "columns=None auto-derives from rows[0].keys() per CONTEXT.md decision"
  - "test_output_result_json_mode_datetime_no_crash named without _table_ per plan spec (plan acceptance criterion grep count of 6 is a minor plan inconsistency — 5 tests match _table_ pattern, 6th is the datetime test)"
metrics:
  duration: "~7 minutes"
  completed: "2026-04-11"
  tasks_completed: 2
  files_modified: 2
---

# Phase 09 Plan 01: Rich Table Rendering in output_result() Summary

**One-liner:** Rich table rendering added to output_result() with columns filtering, single-dict normalization, and auto-column-derivation; 6 new tests cover all table paths.

## What Was Built

Replaced the Phase 08 stub in `output_result()` with a full Rich Table renderer. The function now:

1. Accepts a new keyword parameter `columns: list[str] | None = None`
2. Normalizes a single `dict` input into `[dict]` via `isinstance(data, dict)` check — same rendering path as list input
3. Derives column order from the explicit `columns` list (Phase 10 callers) or falls back to `rows[0].keys()` (auto-detect)
4. Builds a `rich.table.Table`, populates rows using `_cell(row.get(col))` for each column, and renders via `console.print(table)` to stdout
5. Falls through to `typer.echo(str(data))` for plain strings and non-dict/list scalars
6. Existing JSON mode path (`json_mode=True`) unchanged

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement Rich table rendering in output_result() | 372a778 | src/bunny_cdn_sdk/cli/_output.py |
| 2 | Add table-rendering tests to test_app.py | 41360f1 | tests/cli/test_app.py |

## Verification Results

- `uv run pytest tests/cli/test_app.py -v` — 31 passed (0 failures)
- `uv run pytest tests/cli/ -q` — 31 passed, no regressions
- `grep -n "Phase 09 will replace" _output.py` — no output (stub confirmed removed)
- `grep -n "from rich.table import Table" _output.py` — line 14 (confirmed)
- `grep -c "def test_output_result_table_" test_app.py` — 5 (see Deviations note)
- `uv run ty check src/bunny_cdn_sdk/cli/_output.py` — All checks passed

## Decisions Made

1. **Rich Console singleton captures cleanly in pytest:** The existing `console = Console()` singleton at module level outputs plain text when pytest captures via `capsys` (non-TTY environment). No `force_terminal=False` workaround was needed.

2. **`# type: ignore[assignment]` on rows assignment:** `ty` correctly flags the `list[dict[str, Any]]` annotation when assigning from a conditional expression involving `data` (typed as `Any`). The ignore comment is intentional and documented in the plan.

3. **Worktree isolation:** The pytest verification command in the plan specifies `main.git.create-sdk` as the working directory, but this agent's edits live in the `agent-ad8d41d8` worktree. Tests were run from the agent worktree with `uv sync --all-groups --extra cli` to install `[cli]` extras (typer, rich) not present in the fresh worktree `.venv`.

## Deviations from Plan

### Minor Plan Inconsistency (noted, not fixed)

**Plan acceptance criterion:** `grep -c "def test_output_result_table_" tests/cli/test_app.py → returns 6`

**Actual result:** 5 — because `test_output_result_json_mode_datetime_no_crash` (the 6th test) was explicitly named without `_table_` in both the plan's `<behavior>` section and the code block. All 6 new test functions exist and all 31 tests pass. The grep count discrepancy is a minor plan inconsistency, not a missing test.

## Known Stubs

None — `output_result()` stub from Phase 08 has been fully replaced.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes were introduced. T-09-04 mitigation confirmed: `output_result()` uses `console.print(table)` (stdout via `console`), not `err_console`. Error output separation is unchanged.

## Self-Check: PASSED

- `src/bunny_cdn_sdk/cli/_output.py` — exists, contains `from rich.table import Table` at line 14
- `tests/cli/test_app.py` — exists, 254 lines, 31 tests collected
- Commit `372a778` — exists (Task 1: feat)
- Commit `41360f1` — exists (Task 2: test)
- All 31 tests pass with 0 failures
