# Phase 10: CoreClient Sub-Apps — Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Build 4 Typer sub-apps — `pull-zone`, `storage-zone`, `dns-zone`, `video-library` — plus a
top-level `bunnycdn purge <url>` command, all wired to `CoreClient`.

Each sub-app covers full CRUD: list, get, create, delete (with confirmation), and update
(`--set KEY=VALUE`). DNS zones additionally include `record add/update/delete` sub-commands.

All commands have CliRunner-based tests covering: success path, error path (SDK exceptions),
and `--json` flag output.

Out of scope: `StorageClient` commands (Phase 11), stats/billing utilities (Phase 12),
progress bars, config files, shell autocomplete.

</domain>

<decisions>
## Implementation Decisions

### Delete Confirmation

- **D-01:** All delete commands require `typer.confirm()` — no silent deletes.
- **D-02:** `--yes` / `-y` flag available on every delete command to skip the prompt
  (for scripting/CI use cases). When `--yes` is passed, confirmation is skipped entirely.
- **D-03:** Confirmation prompt includes both the resource name AND ID:
  e.g. `"Delete pull zone 12345 (my-pull-zone)? [y/N]"`. Makes the destructive action explicit.
- **D-04:** After a successful delete, print a plain message:
  e.g. `"Deleted pull zone 12345 (my-pull-zone)."` — no table.

### Purge Command

- **D-05:** `bunnycdn purge <url>` is a top-level command registered directly on the root app
  (not nested under a sub-app). Quick to type; stats/billing in Phase 12 can be top-level too.
- **D-06:** On success, print a plain message: `"Purged: <url>"` — no table.

### List Methods

- **D-07:** All `list` commands use iterator methods — `iter_pull_zones`, `iter_storage_zones`,
  `iter_dns_zones`, `iter_video_libraries` — which auto-paginate across all pages.
  Satisfies OUT-03: `--json` path can collect all items from the iterator before serializing.

### Column Curation

**General rules (applied to all commands):**
- **D-08:** Name column is always first when the resource has a `Name` field.
- **D-09:** `Id` is always last.
- **D-10:** List commands sort output alphabetically by `Name` (or `Domain` for DNS zones)
  before passing to `output_result()`.

**Per-resource column lists (passed as `columns=` to `output_result()`):**

| Resource | Columns (in order) |
|----------|--------------------|
| Pull Zone | `["Name", "OriginUrl", "Enabled", "Id"]` |
| Storage Zone | `["Name", "Region", "Id"]` |
| DNS Zone | `["Domain", "RecordsCount", "Id"]` |
| Video Library | `["Name", "VideoCount", "Id"]` |
| DNS Record (add/update output) | `["Name", "Type", "Value", "Id"]` |

- **D-11:** `create` commands display the newly created resource using the same columns as
  the list view (call `output_result(result, columns=[...])` — no separate code path).

### Update Command Output (Diff Display)

- **D-12:** Update commands fetch the resource **before** updating (one extra GET call), then
  apply the PATCH/POST. This gives the "before" state for diffing.
- **D-13:** Output shows a `Field | Before | After` table containing **only the changed rows**
  (fields where before ≠ after). Unchanged fields are omitted.
- **D-14:** Changed values are displayed in **red italic** using Rich `Text` styling
  (e.g. `Text(value, style="bold red italic")`). The Before column shows the old value in red
  italic; the After column shows the new value in red italic.
- **D-15:** If `--json` is passed to an update command, output the updated resource dict as
  JSON (skip the diff display).

### Claude's Discretion

- **Module structure:** 4 separate files (`_pull_zone.py`, `_storage_zone.py`, `_dns_zone.py`,
  `_video_library.py`). DNS record sub-commands live inside `_dns_zone.py` as a nested Typer app.
  Top-level `purge` registered in `_app.py`.
- **`--set` parsing:** `KEY=VALUE` pairs split on first `=`; malformed pairs (no `=`) raise
  `ValueError` which `sdk_errors()` catches and maps to exit 1.
- **Auth guard:** Core commands require `state.api_key`; missing key exits with actionable error.
- **Test structure:** One test file per sub-app module — `test_pull_zone.py`, `test_storage_zone.py`,
  `test_dns_zone.py`, `test_video_library.py` — plus `test_purge.py` for the top-level command.
  Mock at the `CoreClient` boundary (not HTTP), per TEST-01.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CLI Foundation (Phase 08/09)
- `src/bunny_cdn_sdk/cli/_app.py` — root Typer `app`, `State` dataclass, `@app.callback()`
- `src/bunny_cdn_sdk/cli/_output.py` — `output_result()`, `sdk_errors()`, `_cell()`, `console`, `err_console`
- `src/bunny_cdn_sdk/cli/__init__.py` — ImportError guard pattern

### SDK Client
- `src/bunny_cdn_sdk/core.py` — `CoreClient` methods: `iter_pull_zones`, `get_pull_zone`,
  `create_pull_zone`, `update_pull_zone`, `delete_pull_zone`, `purge_pull_zone_cache`,
  `iter_storage_zones`, `get_storage_zone`, `create_storage_zone`, `update_storage_zone`,
  `delete_storage_zone`, `iter_dns_zones`, `get_dns_zone`, `create_dns_zone`, `update_dns_zone`,
  `delete_dns_zone`, `add_dns_record`, `update_dns_record`, `delete_dns_record`,
  `iter_video_libraries`, `get_video_library`, `create_video_library`, `update_video_library`,
  `delete_video_library`, `purge_url`

### Tests
- `tests/cli/conftest.py` — `runner` CliRunner fixture
- `tests/cli/test_app.py` — existing test patterns (mock style, assertion patterns)

### Requirements
- `.planning/REQUIREMENTS.md` — PZ-01–06, SZ-01–05, DZ-01–07, VL-01–05, UTIL-01, TEST-01–03
  are the acceptance criteria for this phase

No external specs or ADRs referenced.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `output_result(data, *, columns, json_mode, _console)` — pass curated column list, let it handle
  Rich table + JSON routing. Single-dict input auto-wraps to single-row table.
- `sdk_errors()` context manager — wraps every command body for consistent error handling.
- `console` / `err_console` singletons — use `err_console.print()` for error messages.
- `State` dataclass on `ctx.obj` — access via `cast("State", ctx.obj)` in every command.

### Established Patterns
- `app.callback()` injects auth into `State` — commands read from `ctx.obj`, never from flags.
- `runner.invoke(app, [...])` in CliRunner tests — mock `CoreClient.__init__` at import time.
- Phase 09 confirmed: `output_result()` with `columns=None` auto-derives headers from first
  dict's keys — but Phase 10 commands MUST pass explicit `columns=` (curated per D-10 above).

### Integration Points
- New sub-apps registered via `app.add_typer(pull_zone_app, name="pull-zone")` in `_app.py`
  (or imported and registered at `cli/__init__.py` import time).
- `CoreClient(api_key=state.api_key)` instantiated inside each command using `sdk_errors()`.

</code_context>

<specifics>
## Specific Ideas

- Update diff table uses Rich `Text(value, style="bold red italic")` for changed cells — both
  Before and After columns of changed rows render in red italic.
- Confirmation prompt wording pattern: `f"Delete {resource_type} {id} ({name})?"` — consistent
  across all 4 resource types.
- Alphabetical sort: `sorted(iter_pull_zones(...), key=lambda z: z.get("Name", ""))` before
  passing to `output_result()`.

</specifics>

<deferred>
## Deferred Ideas

None raised during discussion.

</deferred>

---

*Phase: 10-coreclient-sub-apps*
*Context gathered: 2026-04-11*
