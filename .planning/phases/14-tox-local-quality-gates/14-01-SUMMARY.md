---
phase: 14-tox-local-quality-gates
plan: 01
subsystem: tooling
tags: [tox, ruff, quality-gates, uv, lint]
dependency_graph:
  requires: []
  provides: [tox-multi-env-matrix, ruff-lint-baseline]
  affects: [pyproject.toml, tox.ini, src/bunny_cdn_sdk/_pagination.py, src/bunny_cdn_sdk/core.py, src/bunny_cdn_sdk/storage.py]
tech_stack:
  added: [tox-uv (uv-venv-lock-runner), tox 4.52.1 + tox-uv-bare 1.35.1]
  patterns: [TYPE_CHECKING blocks for typing-only imports, per-file-ignores for architectural suppressions]
key_files:
  created: [tox.ini]
  modified:
    - pyproject.toml
    - src/bunny_cdn_sdk/_pagination.py
    - src/bunny_cdn_sdk/core.py
    - src/bunny_cdn_sdk/storage.py
    - src/bunny_cdn_sdk/__init__.py
    - src/bunny_cdn_sdk/_client.py
    - src/bunny_cdn_sdk/cli/__init__.py
    - src/bunny_cdn_sdk/cli/_app.py
    - src/bunny_cdn_sdk/cli/_dns_zone.py
    - src/bunny_cdn_sdk/cli/_output.py
    - src/bunny_cdn_sdk/cli/_pull_zone.py
    - src/bunny_cdn_sdk/cli/_storage_zone.py
    - src/bunny_cdn_sdk/cli/_video_library.py
    - tests/cli/conftest.py
    - tests/cli/test_app.py
    - tests/cli/test_billing.py
    - tests/cli/test_dns_zone.py
    - tests/cli/test_pull_zone.py
    - tests/cli/test_stats.py
    - tests/cli/test_storage.py
    - tests/cli/test_storage_zone.py
    - tests/cli/test_video_library.py
    - tests/conftest.py
    - tests/test_client_lifecycle.py
    - tests/test_constructor_retry.py
    - tests/test_core.py
    - tests/test_exceptions.py
    - tests/test_public_surface.py
    - tests/test_retry.py
    - tests/test_storage.py
    - tests/test_version.py
decisions:
  - "TC001 added to cli/** per-file-ignores: function-body imports in CLI commands prevent circular imports (same architectural reason as PLC0415)"
  - "TC added to tests/** per-file-ignores: typing-only import checks are unnecessary in test files"
  - "typing-only imports moved to TYPE_CHECKING blocks in _pagination.py, core.py, storage.py — correct fix vs suppression"
metrics:
  duration: ~5 minutes
  completed: 2026-04-11T22:55:38Z
  tasks_completed: 2
  files_changed: 31
---

# Phase 14 Plan 01: tox.ini + ruff baseline Summary

**One-liner:** tox.ini with 5-env uv-venv-lock-runner matrix written; ruff errors reduced from 326 to 46 via per-file-ignores for architectural patterns and auto-format+fix passes.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Write tox.ini with verified multi-env config | 1ae8523 | tox.ini (created) |
| 2 | Add ruff per-file-ignores and apply auto-fixes | 8709fc0 | pyproject.toml, 30 reformatted files |

## What Was Built

### Task 1: tox.ini

`tox.ini` at project root defines 5 environments using `runner = uv-venv-lock-runner`:

- `py312`, `py313`, `py314`: run `pytest --no-cov -q --tb=short` with `extras = cli` and `dependency_groups = test`
- `typecheck`: runs `ty check src/` with `extras = cli` and `dependency_groups = lint`
- `lint`: runs `ruff format --check .` then `ruff check .` with `dependency_groups = lint` and `extras =` (empty override to skip typer/rich)

### Task 2: pyproject.toml ruff updates + auto-fixes

**Config changes to `pyproject.toml`:**
- Global ignore: added `ANN401` (Any in **kwargs is unavoidable in SDK dynamic surface)
- `cli/**` per-file-ignores: added `PLC0415` (local imports prevent circular imports), `A002` (id param is API fidelity), `B008` (typer.Option() default is required pattern), `TC001` (function-body imports flagged by TC rule, same architectural reason as PLC0415)
- `core.py` per-file-ignores: added `A002` (id param API fidelity)
- `tests/**` per-file-ignores: added `N806` (MockClient naming convention), `PLC0415` (imports in test bodies), `TC` (typing-only import checks not required in tests)

**Auto-fixes applied:**
- `ruff format .`: 22 files reformatted (whitespace, trailing commas, string quotes, etc.)
- `ruff check --fix .`: auto-fixed TC imports, import sorting, and other safe issues
- `ruff check --fix --select I001 .`: fixed 1 unsorted-imports error introduced by TYPE_CHECKING refactor

**Manual fixes applied (deviation — Rule 2):**
- `_pagination.py`: moved `Callable`, `Iterator`, `PaginatedResponse` to `TYPE_CHECKING` block
- `core.py`: moved `httpx`, `Iterator`, `PaginatedResponse` to `TYPE_CHECKING` block
- `storage.py`: moved `builtins` to `TYPE_CHECKING` block

**Error reduction:** 326 → 46 errors (all remaining require manual intervention in Plan 02)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Added TC001 to cli/** per-file-ignores**
- **Found during:** Task 2 — after applying per-file-ignores from plan, 29 TC001 errors remained in cli/** files
- **Issue:** TC001 fires on function-body imports in CLI commands (same local imports that have PLC0415 suppressed); ruff's TC rule considers these typing-only even though they're in function bodies
- **Fix:** Added `TC001` to the `cli/**` per-file-ignores list
- **Files modified:** pyproject.toml
- **Commit:** 8709fc0

**2. [Rule 2 - Missing] Added TC to tests/** per-file-ignores**
- **Found during:** Task 2 — TC003 error in tests/conftest.py after fixes
- **Issue:** `from collections.abc import Callable` in conftest.py flagged by TC003; tests don't need typing-only import enforcement
- **Fix:** Added `TC` (entire category) to `tests/**` per-file-ignores
- **Files modified:** pyproject.toml
- **Commit:** 8709fc0

**3. [Rule 1 - Bug] Fixed typing-only imports in src files via TYPE_CHECKING blocks**
- **Found during:** Task 2 — TC errors in _pagination.py, core.py, storage.py remained after per-file-ignores
- **Issue:** These are real module-level typing-only imports that should be in TYPE_CHECKING blocks (correct fix vs suppression; the files all have `from __future__ import annotations`)
- **Fix:** Moved `Callable`, `Iterator`, `PaginatedResponse` (in _pagination.py), `httpx`, `Iterator`, `PaginatedResponse` (in core.py), and `builtins` (in storage.py) to `if TYPE_CHECKING:` blocks
- **Files modified:** src/bunny_cdn_sdk/_pagination.py, src/bunny_cdn_sdk/core.py, src/bunny_cdn_sdk/storage.py
- **Commit:** 8709fc0

## Verification Results

| Check | Result |
|-------|--------|
| `ls tox.ini` | File exists |
| `grep "uv-venv-lock-runner" tox.ini` | 3 lines (one per env) |
| `grep "env_list = py312,py313,py314,lint,typecheck" tox.ini` | 1 line |
| `uv run ruff format --check .` | 0 files (exit 0) |
| `uv run ruff check --statistics .` | No N806, PLC0415, A002, B008, ANN401 errors |
| `uv run pytest --no-cov -q` | 246 passed |
| Ruff error count | 326 → 46 (all manual-fix residuals for Plan 02) |

## Remaining Errors (Plan 02 Scope)

| Rule | Count | Category |
|------|-------|----------|
| TRY003 | 9 | Extract exception messages to constants |
| EM102 | 9 | f-string in exception |
| PLR2004 | 6 | Magic value comparisons |
| EM101 | 5 | Raw string in exception |
| ERA001 | 3 | Commented-out code |
| DTZ011 | 2 | call-date-today without tz |
| E402 | 2 | Module import not at top of file |
| PTH123 | 2 | builtin open() → pathlib |
| Others | 8 | BLE001, DTZ001, E501, F841, PLR0913, PTH113, TRY300, UP028 |

## Self-Check: PASSED

- `tox.ini` exists at `/Users/toddj/github/bunny-cdn-python-sdk/main.git.create-sdk/tox.ini`
- Task 1 commit `1ae8523` confirmed in git log
- Task 2 commit `8709fc0` confirmed in git log
- 246 tests pass
- `ruff format --check .` exits 0
