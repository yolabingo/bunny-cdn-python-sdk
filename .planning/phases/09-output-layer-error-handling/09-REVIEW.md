---
phase: 09-output-layer-error-handling
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/bunny_cdn_sdk/cli/_output.py
  - tests/cli/test_app.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-04-11
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

The output layer is well-structured overall. The exception handler ordering in `sdk_errors()` is correct — subclasses are caught before their base class, and the `BunnyTimeoutError`/`BunnyConnectionError` ordering is also correct. The `_cell()` helper is clean.

Two substantive issues were found: a crash path when `output_result()` receives a list of non-dict elements, and a reliability gap in the test suite where Rich's module-level `Console` object bypasses `capsys` capture. Two additional info-level items cover a silent no-output case and a missing coverage test.

## Warnings

### WR-01: `output_result()` crashes on list of non-dict elements

**File:** `src/bunny_cdn_sdk/cli/_output.py:82-96`

**Issue:** The guard at line 77 short-circuits only when the top-level `data` is not a `dict` or `list`. When `data` is a `list` containing non-dict elements (e.g., `["a", "b"]` or `[1, 2]`), the code falls through to the table-rendering path. Line 82 casts the list directly into `rows: list[dict[str, Any]]` (suppressing the type error with `type: ignore[assignment]`). Line 96 then calls `row.get(col)` on each element. If any element is not a dict, this raises `AttributeError` at runtime — unhandled, and not caught by `sdk_errors()` (which only catches `ValueError`, not `AttributeError`).

**Fix:** Add an element-type check before entering the table rendering path, or handle non-dict lists as plain output. The simplest safe approach:

```python
# After the rows normalization on line 82, add:
if rows and not isinstance(rows[0], dict):
    # List of scalars — render as plain lines
    for item in rows:
        typer.echo(str(item))
    return
```

Alternatively, if a `list` of scalars is not a supported input shape, document and reject it explicitly:

```python
if rows and not isinstance(rows[0], dict):
    raise ValueError(f"output_result() expects a list of dicts; got list of {type(rows[0]).__name__}")
```

---

### WR-02: Rich table tests may not capture output via `capsys` — silent false positives

**File:** `tests/cli/test_app.py:209-254`

**Issue:** `console = Console()` in `_output.py` is instantiated at module import time (line 27). Rich's `Console` records the real `sys.stdout` file descriptor at construction. The `capsys` pytest fixture works by temporarily swapping `sys.stdout` to a `StringIO` buffer after module import. As a result, `console.print(table)` writes to the original `sys.stdout`, not the captured buffer. All eight table-rendering tests that assert `"Id" in captured.out`, `"42" in captured.out`, etc., may be testing against an empty string — the assertion passes vacuously if the Rich output bypasses capture.

The plain-string tests (`test_output_result_plain_mode`, etc.) use `typer.echo()` which reads `sys.stdout` at call time and is captured correctly by `capsys`.

**Fix:** Restructure `output_result()` to accept an optional `console` parameter (or use `Console(file=sys.stdout)` so it re-reads the file handle at print time), and in tests pass a `Console` backed by a `StringIO`:

```python
# _output.py: accept optional console parameter
def output_result(
    data: Any,
    *,
    columns: list[str] | None = None,
    json_mode: bool = False,
    _console: Console | None = None,
) -> None:
    _con = _console or console
    ...
    _con.print(table)
```

```python
# In tests, inject a captured console:
from io import StringIO
from rich.console import Console

def test_output_result_table_list_shows_column_headers() -> None:
    buf = StringIO()
    con = Console(file=buf, highlight=False)
    output_result([{"Id": 1, "Name": "a"}], columns=["Id", "Name"], json_mode=False, _console=con)
    out = buf.getvalue()
    assert "Id" in out
    assert "Name" in out
```

An alternative without changing the signature is to monkeypatch `bunny_cdn_sdk.cli._output.console` in each test with a `Console(file=buf)`.

## Info

### IN-01: Silent no-output when list is empty and no columns provided

**File:** `src/bunny_cdn_sdk/cli/_output.py:84-89`

**Issue:** When `data` is an empty list and `columns` is `None`, the function returns with no output at all. A user running a CLI command that returns zero results sees nothing — no message, no empty table, no indication that the call succeeded. This is a UX dead end that could be mistaken for a hang or an error.

**Fix:** Emit a brief message when the result set is empty:

```python
if not rows:
    if columns:
        table = Table(*columns)
        console.print(table)
    else:
        typer.echo("(no results)")
    return
```

---

### IN-02: No test exercises `BunnySDKError` base class directly in `sdk_errors()`

**File:** `tests/cli/test_app.py` (missing test)

**Issue:** The `sdk_errors()` handler at `_output.py:57-59` catches `BunnySDKError` as a final catch-all for any SDK error not matched by a more specific handler. There is no test that raises a bare `BunnySDKError` instance to verify this branch. If the handler were accidentally removed or the except clause changed, no test would fail.

**Fix:** Add a test:

```python
def test_sdk_errors_catches_sdk_error_base() -> None:
    from bunny_cdn_sdk._exceptions import BunnySDKError

    with pytest.raises(typer.Exit) as exc_info:
        with sdk_errors():
            raise BunnySDKError("unexpected sdk failure")
    assert exc_info.value.exit_code == 1
```

---

_Reviewed: 2026-04-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
