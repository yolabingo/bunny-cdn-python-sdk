# Phase 09: Output Layer & Error Handling — Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Fill in the Rich table rendering stub in `output_result()` — replacing the Phase 08 placeholder
(`# Phase 09 will replace this with Rich table rendering`) with actual Rich Table output.

`sdk_errors()`, `_cell()`, the JSON path of `output_result()`, and the `console`/`err_console`
singletons are **already shipped and tested** in Phase 08. Phase 09 adds only:

1. Rich table rendering in the non-JSON path of `output_result()`
2. A `columns: list[str] | None = None` parameter on `output_result()`
3. Unit tests covering the table-rendering paths (list input, single-dict input, columns filtering)

Out of scope: no new exception types, no changes to `sdk_errors()` or `_cell()`, no CLI commands,
no changes to `_app.py`.

</domain>

<decisions>
## Implementation Decisions

### `output_result()` signature — columns parameter

**Decision (locked):** Add `columns: list[str] | None = None` to `output_result()`.

Final signature:
```python
def output_result(
    data: Any,
    *,
    columns: list[str] | None = None,
    json_mode: bool = False,
) -> None:
```

**Why:** Bunny API responses contain 50+ fields. Phase 10 commands need to curate which fields
appear in the table (e.g., `["Id", "Name", "OriginUrl", "Enabled"]` for pull zones). Without a
`columns` param, every table would be extremely wide and unusable.

**Calling convention for Phase 10:**
```python
output_result(
    list(iter_pull_zones()),
    columns=["Id", "Name", "OriginUrl", "Enabled"],
    json_mode=state.json_output,
)
```

**When `columns` is None:** Auto-derive columns from all keys of the first dict in the data.
This is the fallback for ad-hoc use, not the expected path for Phase 10 commands.

---

### Single-resource table format — single-row table

**Decision (locked):** For `get` commands returning a single dict, render as a **single-row table**
using the same columns as the list view (i.e., the `columns` param determines what shows).

```
┌───────┬──────────────┬─────────────────────┬─────────┐
│ Id    │ Name         │ OriginUrl           │ Enabled │
├───────┼──────────────┼─────────────────────┼─────────┤
│ 12345 │ my-pull-zone │ https://example.com │ True    │
└───────┴──────────────┴─────────────────────┴─────────┘
```

**Detection:** `output_result()` detects a single resource by checking `isinstance(data, list)`.
If False, wrap in `[data]` before rendering — same code path as list, single row.

---

### `output_result()` behavior matrix

| `data` type | `json_mode` | Behavior |
|-------------|-------------|----------|
| `list[dict]` | False | Rich table, columns from `columns=` (or auto-detect from first item) |
| `dict` | False | Rich table, single row, same columns logic |
| `list[dict]` | True | `json.dumps(data, indent=2, default=str)` to stdout |
| `dict` | True | `json.dumps(data, indent=2, default=str)` to stdout |
| `str` or scalar | False | `typer.echo(str(data))` — passthrough for simple messages |

---

### Test scope for Phase 09

Phase 08 already tests: `sdk_errors()`, `_cell()`, `output_result()` JSON mode, plain-mode stub.

Phase 09 adds tests for:
- `output_result()` with a list of dicts in table mode → Rich table renders (check row count, column headers)
- `output_result()` with a single dict in table mode → single-row table renders
- `output_result()` with `columns=` → only specified fields appear
- `output_result()` with `columns=None` → auto-derives columns from first dict's keys
- `output_result()` with non-serializable value (e.g., `datetime`) in JSON mode → `default=str` prevents crash (OUT-06)

**Note:** Tests use `capsys` or `CliRunner` capture. Rich tables contain ANSI escape codes in
terminal mode — tests should strip ANSI or assert on plain content (Rich's `Console(force_terminal=False)`).

---

### Claude's Discretion

- Column header formatting: strip nothing — use API field names as-is (Phase 10 will pass curated column lists with the exact names it wants displayed)
- `_cell()` integration: call `_cell(row[col])` for each cell in the table — existing behavior is correct
- Rich `Table` style: default Rich styling is fine; no custom theme
- Missing column key in a row: use `_cell(row.get(col))` → `_cell(None)` → `""`
- `console.print(table)` for output (not `typer.echo`) — already using Rich Console in this module

</decisions>

<canonical_refs>
## Canonical References

- `src/bunny_cdn_sdk/cli/_output.py` — file to modify (replace `output_result()` stub)
- `tests/cli/test_app.py` — file to extend (add table-rendering tests)
- `src/bunny_cdn_sdk/_exceptions.py` — exception hierarchy used by `sdk_errors()` (read-only)
- `.planning/REQUIREMENTS.md` — OUT-01 through OUT-06 are the acceptance criteria for this phase

No external specs or ADRs referenced.
</canonical_refs>

<deferred>
## Deferred Ideas

None raised during discussion.
</deferred>
