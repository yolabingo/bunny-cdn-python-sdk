---
phase: 08-cli-scaffold
fixed_at: 2026-04-10T00:00:00Z
review_path: .planning/phases/08-cli-scaffold/08-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 08: Code Review Fix Report

**Fixed at:** 2026-04-10
**Source review:** .planning/phases/08-cli-scaffold/08-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: `sdk_errors()` silently swallows unhandled `BunnySDKError` subclasses

**Files modified:** `src/bunny_cdn_sdk/cli/_output.py`
**Commit:** 54c13c8
**Applied fix:** Added `BunnySDKError` to the imports from `bunny_cdn_sdk._exceptions`, then added a `except BunnySDKError as exc` catch-all clause after the `BunnyConnectionError` handler and before `ValueError`. This ensures any future `BunnySDKError` subclass that does not inherit from `BunnyAPIError` or `BunnyConnectionError` produces a clean stderr message and `Exit(1)` rather than a raw traceback.

---

### WR-02: `_mock_exc` helper in tests has a misleading return-type annotation

**Files modified:** `tests/cli/test_app.py`
**Commit:** d2d6a9c
**Applied fix:** Changed the `cls` parameter annotation from the bare unparameterized `type` to `type[BunnyAPIError]`. This aligns the annotation with the actual return type, guards against accidentally passing non-`BunnyAPIError` subclasses, and removes the `Unknown` return-type inference issue for `ty`.

---

### WR-03: `bunnycdn` entry point loads CLI dependencies at import time without install guard

**Files modified:** `src/bunny_cdn_sdk/cli/__init__.py`
**Commit:** 3c13bbe
**Applied fix:** Moved `from bunny_cdn_sdk.cli._app import app` from outside the `try/except` block to inside it (as the third import in the `try` body). Removed the now-unnecessary `# noqa: E402` comment. Any `ImportError` raised by `_app.py` or its transitive imports will now be caught and re-raised as the helpful install-hint message rather than propagating as a raw `ImportError`.

---

_Fixed: 2026-04-10_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
