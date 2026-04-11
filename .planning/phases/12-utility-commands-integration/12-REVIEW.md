---
phase: 12-utility-commands-integration
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - tests/cli/test_stats.py
  - tests/cli/test_billing.py
  - src/bunny_cdn_sdk/cli/_app.py
  - README.md
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-04-11
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the stats and billing CLI commands, their tests, and the README CLI section added in phase 12. The implementation is clean and well-structured overall. `billing_cmd` and `stats_cmd` follow established patterns in the codebase, and the test coverage is thorough. Three warnings were found: a deprecated `asyncio.get_event_loop()` call that will raise a `DeprecationWarning` on Python 3.12+ and fail outright in a future release, a silent data-loss risk when `get_statistics()` returns `None`, and a test import that is unused. Three info-level items cover a missing `pytest` import in the billing test, duplicate default-date logic that could be extracted, and a README code snippet that calls a non-existent method name.

---

## Warnings

### WR-01: `asyncio.get_event_loop()` deprecated on Python 3.12+

**File:** `src/bunny_cdn_sdk/cli/_app.py:165`

**Issue:** `_fetch_all()` calls `asyncio.get_event_loop()` to get a loop for `run_in_executor`. On Python 3.10+ this emits a `DeprecationWarning` when there is no current running loop, and on Python 3.12 it raises a `DeprecationWarning` in many contexts. Since this function is only called via `asyncio.run(_fetch_all())` — which creates a new event loop — using `asyncio.get_event_loop()` inside an already-running coroutine is redundant and will break in a future Python version. The correct pattern inside an `async def` is `asyncio.get_running_loop()`.

**Fix:**
```python
async def _fetch_all() -> list[dict]:
    loop = asyncio.get_running_loop()   # replaces get_event_loop()

    async def _one(z: dict) -> dict:
        s = await loop.run_in_executor(
            None,
            lambda: client.get_statistics(
                pullZoneId=z["Id"], dateFrom=date_from, dateTo=date_to
            ),
        )
        return _build_stats_row(z.get("Name", ""), s)

    return list(await asyncio.gather(*(_one(z) for z in zones)))
```

---

### WR-02: `get_statistics()` returning `None` causes unhandled `TypeError` in `_build_stats_row`

**File:** `src/bunny_cdn_sdk/cli/_app.py:172-174`

**Issue:** If `client.get_statistics(...)` returns `None` (e.g., the API returns a 204 or the SDK returns `None` for an empty body), `_build_stats_row(z.get("Name", ""), s)` is called with `s=None`. Inside `_build_stats_row`, the first `stats.get(...)` call will raise `AttributeError: 'NoneType' object has no attribute 'get'`, crashing the entire concurrent gather rather than producing a graceful degraded row. The same applies to the single-zone path at line 159.

**Fix:** Guard against `None` at the call site or inside `_build_stats_row`:
```python
# Option A — guard in _build_stats_row (handles both paths)
def _build_stats_row(name: str, stats: dict | None) -> dict:
    if stats is None:
        stats = {}
    served = stats.get("RequestsServed", 0) or 0
    ...
```

---

### WR-03: Unused `import pytest` in test_stats.py and test_billing.py

**File:** `tests/cli/test_stats.py:8`, `tests/cli/test_billing.py:9`

**Issue:** Both test files import `pytest` but never use it — no `@pytest.mark.*`, `pytest.raises`, or `pytest.fixture` is present in either file. While not a runtime bug, unused imports can cause linting failures in CI and add noise to imports.

**Fix:** Remove the unused `import pytest` from both files.

---

## Info

### IN-01: Unused `BunnyAPIError` import in both test files

**File:** `tests/cli/test_stats.py:10`, `tests/cli/test_billing.py:10`

**Issue:** Both files import `BunnyAPIError` from `bunny_cdn_sdk._exceptions` but it is never referenced in any test. Only `BunnyAuthenticationError` is actually used. This will be flagged by `ruff` (F401).

**Fix:** Remove `BunnyAPIError` from the import in both files:
```python
# test_stats.py and test_billing.py
from bunny_cdn_sdk._exceptions import BunnyAuthenticationError
```

---

### IN-02: Default date range computed redundantly — consider extracting helper

**File:** `src/bunny_cdn_sdk/cli/_app.py:151-152`

**Issue:** The default `dateFrom`/`dateTo` logic (7 days ago → today) is computed inline inside `stats_cmd`. If a future command needs the same defaults, the logic will be duplicated. This is currently a minor duplication, but worth noting for maintainability.

**Fix:** Extract to a small private helper:
```python
def _default_date_range(days: int = 7) -> tuple[str, str]:
    today = date.today()
    return (today - timedelta(days=days)).isoformat(), today.isoformat()
```

---

### IN-03: README Quick Start references non-existent `list_pull_zones()` method

**File:** `README.md:19`

**Issue:** The Quick Start snippet calls `core.list_pull_zones()`, but the CoreClient API documented just below uses `iter_pull_zones()` for auto-pagination. If the SDK exposes both names, `list_pull_zones()` should also appear in the CoreClient section (it currently does not). If only `iter_pull_zones()` exists, the Quick Start example is broken and will raise `AttributeError` for new users.

**Fix:** Verify that `CoreClient.list_pull_zones()` is a real method. If it is, add it to the CoreClient section. If it is not, update the Quick Start example to use `iter_pull_zones()`:
```python
zones = list(core.iter_pull_zones())
```

---

_Reviewed: 2026-04-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
