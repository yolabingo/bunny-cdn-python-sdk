---
phase: 08-cli-scaffold
reviewed: 2026-04-10T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - pyproject.toml
  - src/bunny_cdn_sdk/cli/__init__.py
  - src/bunny_cdn_sdk/cli/_app.py
  - src/bunny_cdn_sdk/cli/_output.py
  - tests/cli/__init__.py
  - tests/cli/conftest.py
  - tests/cli/test_app.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-04-10
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

The CLI scaffold is well-structured. The Typer app wiring, State dataclass, and `sdk_errors()` context manager are implemented correctly. The exception handler ordering in `sdk_errors()` is correct — all subclasses appear before their base classes. The test coverage is solid and exercises the key contracts.

Three warnings and three info items were found. None are blockers, but two warnings are logic correctness concerns worth addressing before Phase 09 adds real subcommands.

## Warnings

### WR-01: `sdk_errors()` silently swallows unhandled `BunnySDKError` subclasses

**File:** `src/bunny_cdn_sdk/cli/_output.py:30-57`

**Issue:** The context manager catches `BunnyAPIError`, `BunnyConnectionError`, and `BunnyTimeoutError`, but `BunnyTimeoutError` is a subclass of `BunnyConnectionError` (and is already caught before it). More importantly, `BunnySDKError` itself is not caught. If a future subclass of `BunnySDKError` that does not inherit from either `BunnyAPIError` or `BunnyConnectionError` is raised inside `sdk_errors()`, it propagates unhandled to Typer, producing a raw traceback instead of a clean error message.

The current hierarchy is:
```
BunnySDKError
├── BunnyAPIError          ← caught (line 46)
│   ├── BunnyAuthenticationError  ← caught (line 34)
│   ├── BunnyNotFoundError        ← caught (line 37)
│   ├── BunnyRateLimitError       ← caught (line 41)
│   └── BunnyServerError          ← caught (line 43)
└── BunnyConnectionError   ← caught (line 53)
    └── BunnyTimeoutError  ← caught (line 49)
```

**Fix:** Add a `BunnySDKError` catch-all after the specific handlers:
```python
except BunnySDKError as exc:
    err_console.print(f"SDK error: {exc}")
    raise typer.Exit(1) from None
```

---

### WR-02: `_mock_exc` helper in tests has a misleading return-type annotation

**File:** `tests/cli/test_app.py:85`

**Issue:** The function is annotated `-> BunnyAPIError` but its `cls` parameter is typed as `type` (bare, unparameterized). Since `ty` has `error-on-warning = true` and `possibly-unresolved-reference = "error"`, this may fail type checking when `ty` tries to infer the return type of `cls(...)` — `type` is untyped, so the return type is `Unknown`, not `BunnyAPIError`. More concretely, the annotation obscures the fact that callers receive a subclass instance, not necessarily a `BunnyAPIError`.

**Fix:** Use a `TypeVar` or `type[BunnyAPIError]` to tighten the signature:
```python
def _mock_exc(
    cls: type[BunnyAPIError],
    status_code: int = 400,
    message: str = "test error",
) -> BunnyAPIError:
```
This also serves as a guard — callers passing a non-`BunnyAPIError` subclass (e.g., accidentally passing `BunnyConnectionError`) will be caught statically.

---

### WR-03: `bunnycdn` entry point loads CLI dependencies at import time without install guard

**File:** `pyproject.toml:24` / `src/bunny_cdn_sdk/cli/__init__.py:10-16`

**Issue:** The `[project.scripts]` entry point maps `bunnycdn` to `bunny_cdn_sdk.cli:app`. When a user installs the base package (`pip install bunny-cdn-sdk`, no `[cli]` extra), running `bunnycdn` triggers the `ImportError` guard in `__init__.py` and prints the helpful install message — this works. However, the import of `_app.py` at line 16 is *outside* the `try/except` block. If `_app.py` itself raises any `ImportError` unrelated to `typer`/`rich` (e.g., from `_output.py`'s imports of SDK internals), the raw `ImportError` propagates without the helpful message.

**Fix:** Wrap the `_app.py` import inside the same `try/except`, or move it before the guard and restructure:
```python
try:
    import typer  # noqa: F401
    from rich.console import Console  # noqa: F401
    from bunny_cdn_sdk.cli._app import app  # move inside the guard
except ImportError as _err:
    raise ImportError(_MSG) from _err
```
Note: this is a minor risk since `_app.py` currently only imports `typer` and stdlib, but it will matter as `_app.py` grows to import SDK client classes.

---

## Info

### IN-01: `output_result()` uses `typer.echo(str(data))` for non-JSON mode — data loss on complex types

**File:** `src/bunny_cdn_sdk/cli/_output.py:66`

**Issue:** The plain-mode fallback calls `str(data)` on arbitrary `Any` data. For dicts and lists this produces Python `repr`-style output (e.g., `{'key': 'value'}`), which is not valid JSON and not formatted. The docstring acknowledges this is temporary ("Phase 09 will replace this with Rich table rendering"), so it is intentional, but it means the plain-mode path is currently non-functional for structured data.

**Fix:** No action needed until Phase 09. Consider adding a `# pragma: no cover` or a `# TODO(phase-09):` comment to signal this is a known stub, so it doesn't trigger coverage failures as subcommands are added.

---

### IN-02: `_cell()` dict formatting does not escape `=` in keys or values

**File:** `src/bunny_cdn_sdk/cli/_output.py:74`

**Issue:** `", ".join(f"{k}={v}" for k, v in value.items())` produces ambiguous output if a key or value contains `=` or `,`. For example, `{"a=b": "c"}` renders as `a=b=c`. Since `_cell()` is a table-cell formatter, this is an edge case with low immediate risk, but it will become relevant once Phase 09 adds real API data rendering.

**Fix:** Document the limitation or add escaping. For Phase 08 scope, a comment is sufficient:
```python
# NOTE: keys/values with '=' or ',' produce ambiguous output; revisit in Phase 09
return ", ".join(f"{k}={v}" for k, v in value.items())
```

---

### IN-03: `test_no_args_shows_help` accepts exit code 0 or 2 without explanation

**File:** `tests/cli/test_app.py:41-43`

**Issue:** The assertion `assert result.exit_code in (0, 2)` accepts both exit codes, with a comment noting "Typer shows help and exits 2 in CliRunner context." This is a test reliability issue — the accepted range is wider than necessary. If Typer's behavior changes in a patch release, a regression might still pass this test.

**Fix:** Pin the expected exit code to 0 (which `no_args_is_help=True` should produce), or test the exact Typer version behavior:
```python
# no_args_is_help=True exits 0 per Typer docs; 2 is a CliRunner artifact in some versions
assert result.exit_code == 0
```
If exit code 2 is genuinely observed in CI, add a version comment and open an issue to track it.

---

_Reviewed: 2026-04-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
