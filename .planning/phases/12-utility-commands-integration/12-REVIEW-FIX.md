---
phase: 12-utility-commands-integration
fixed_at: 2026-04-11T00:00:00Z
review_path: .planning/phases/12-utility-commands-integration/12-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 12: Code Review Fix Report

**Fixed at:** 2026-04-11
**Source review:** .planning/phases/12-utility-commands-integration/12-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: `asyncio.get_event_loop()` deprecated on Python 3.12+

**Files modified:** `src/bunny_cdn_sdk/cli/_app.py`
**Commit:** b633514
**Applied fix:** Replaced `asyncio.get_event_loop()` with `asyncio.get_running_loop()` inside `_fetch_all()`. Since this coroutine is always invoked via `asyncio.run()`, a running loop is always present and `get_running_loop()` is the correct, deprecation-free API.

### WR-02: `get_statistics()` returning `None` causes unhandled `TypeError` in `_build_stats_row`

**Files modified:** `src/bunny_cdn_sdk/cli/_app.py`
**Commit:** 580efaa
**Applied fix:** Updated `_build_stats_row` signature to `stats: dict | None` and added an early guard (`if stats is None: stats = {}`) before any `.get()` calls. This covers both the single-zone path (line 160) and the concurrent-gather path (line 174) without modifying call sites.

### WR-03: Unused `import pytest` in test_stats.py and test_billing.py

**Files modified:** `tests/cli/test_stats.py`, `tests/cli/test_billing.py`
**Commit:** dbefa14
**Applied fix:** Removed the unused `import pytest` line from both test files. Neither file uses any `pytest` symbols directly (`pytest.mark`, `pytest.raises`, etc.), so the import was dead code that would trigger ruff F401.

---

_Fixed: 2026-04-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
