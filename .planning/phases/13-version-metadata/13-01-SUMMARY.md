---
phase: 13-version-metadata
plan: "01"
subsystem: packaging
tags: [version, metadata, pypi, importlib]
dependency_graph:
  requires: []
  provides: [runtime-version-attribute, complete-pypi-metadata]
  affects: [pyproject.toml, src/bunny_cdn_sdk/__init__.py]
tech_stack:
  added: []
  patterns: [importlib.metadata version sourcing]
key_files:
  created:
    - tests/test_version.py
  modified:
    - src/bunny_cdn_sdk/__init__.py
    - pyproject.toml
decisions:
  - "importlib.metadata.version('bunny-cdn-sdk') with hyphen matches pyproject.toml name field"
  - "Version bumped to 2.1.0 to reflect current milestone"
  - "__version__ added as first entry in __all__ for public API visibility"
metrics:
  duration: ~8 minutes
  completed: "2026-04-11T22:03:19Z"
  tasks_completed: 2
  files_changed: 3
---

# Phase 13 Plan 01: Version Metadata Summary

**One-liner:** `bunnycdn.__version__` wired to `importlib.metadata` with version bumped to 2.1.0 and complete PyPI classifiers, license, keywords, and project URLs added to pyproject.toml.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add `__version__` via importlib.metadata | 9ff877b | src/bunny_cdn_sdk/__init__.py, tests/test_version.py |
| 2 | Complete pyproject.toml package metadata | d0b307d | pyproject.toml |

## What Was Built

### Task 1: `__version__` via importlib.metadata

`src/bunny_cdn_sdk/__init__.py` now exposes `__version__` sourced entirely from the installed package metadata (pyproject.toml). Added:

```python
import importlib.metadata

__version__ = importlib.metadata.version("bunny-cdn-sdk")
```

And `"__version__"` added as the first entry in `__all__`. No version literal in `__init__.py`.

A TDD test suite was created at `tests/test_version.py` covering:
- Attribute exists on package
- Is a non-empty string
- Matches `importlib.metadata.version("bunny-cdn-sdk")`
- Is in `__all__`
- No bare string literal in `__init__.py`

### Task 2: Complete pyproject.toml metadata

Updated `[project]` section with all fields required for a complete PyPI listing:

- **Version:** `0.1.0` → `2.1.0`
- **readme:** `README.md` (wires PyPI long description)
- **license:** `{ text = "MIT" }`
- **keywords:** `["bunny", "cdn", "bunnycdn", "api", "sdk"]`
- **classifiers:** Full list including Development Status Beta, Python 3.12/3.13/3.14, MIT License, Typing::Typed
- **[project.urls]:** Homepage, Repository, Bug Tracker

## Verification Results

```
$ uv run python -c "import bunny_cdn_sdk; print(bunny_cdn_sdk.__version__)"
2.1.0

$ grep -n "__version__" src/bunny_cdn_sdk/__init__.py
8:__version__ = importlib.metadata.version("bunny-cdn-sdk")
25:    "__version__",

$ uv run pytest tests/test_version.py -q
5 passed

$ uv run pytest -q  (with cli extras)
246 passed
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

No new security-relevant surface introduced. `importlib.metadata` is Python stdlib with no supply chain risk. All pyproject.toml values are maintainer-controlled literals.

## Self-Check: PASSED

- `src/bunny_cdn_sdk/__init__.py` — contains `importlib.metadata.version("bunny-cdn-sdk")` and `"__version__"` in `__all__`
- `pyproject.toml` — version `2.1.0`, classifiers, license, readme, keywords, [project.urls] all present
- `tests/test_version.py` — 5 tests, all passing
- Commit `9ff877b` exists: feat(13-01): add __version__ via importlib.metadata
- Commit `d0b307d` exists: feat(13-01): complete pyproject.toml package metadata
