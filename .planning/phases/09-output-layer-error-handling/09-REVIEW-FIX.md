---
phase: 09-output-layer-error-handling
fixed_at: 2026-04-11T00:00:00Z
review_path: .planning/phases/09-output-layer-error-handling/09-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 09: Code Review Fix Report

**Fixed at:** 2026-04-11
**Source review:** .planning/phases/09-output-layer-error-handling/09-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: `output_result()` crashes on list of non-dict elements

**Files modified:** `src/bunny_cdn_sdk/cli/_output.py`
**Commit:** 635113b
**Applied fix:** Added a guard immediately after the rows normalization step. When `rows` is non-empty and its first element is not a `dict`, each element is echoed as a plain string via `typer.echo(str(item))` and the function returns early — preventing the `AttributeError` that would occur when `row.get(col)` is called on a non-dict value in the table-rendering loop.

### WR-02: Rich table tests may not capture output via `capsys` — silent false positives

**Files modified:** `src/bunny_cdn_sdk/cli/_output.py`, `tests/cli/test_app.py`
**Commit:** 8d7b0bc
**Applied fix:** Added an optional `_console: Console | None = None` keyword parameter to `output_result()`. Inside the function, `_con = _console or console` selects the injected console when provided, falling back to the module-level `console` for production use. All five Rich table-rendering tests were rewritten to drop `capsys` and instead inject a `Console(file=buf, highlight=False)` backed by a `StringIO`, reading from `buf.getvalue()` after the call. A shared `_make_console()` helper was added to reduce boilerplate. All 31 tests pass.

---

_Fixed: 2026-04-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
