# Phase 12: Utility Commands & Integration — Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver two top-level commands (`stats`, `billing`) registered directly on the root app (same
pattern as `purge` — D-05 from Phase 10), plus a concise README CLI section.

This completes the v2.0 Typer CLI milestone.

**In scope:**
- `bunnycdn stats` — per-zone stats report (concurrent API calls, async internally)
- `bunnycdn billing` — account billing summary (single `get_billing()` call)
- CliRunner tests for both commands (same pattern as Phases 10/11)
- README `## CLI` section (concise reference: install, command groups, env var table, jq example)

**Out of scope:**
- `--include-billing` flag on stats (deferred — billing attribution is account-level only)
- Per-zone cost breakdown (Bunny `/billing` endpoint does not support per-zone attribution)
- Shell autocomplete, config file, progress bars

</domain>

<decisions>
## Implementation Decisions

### stats command — design

- **D-01:** `bunnycdn stats` is a **per-zone report**: call `iter_pull_zones()` to get all zones,
  then call `get_statistics(pullZoneId=id)` for each zone concurrently using async batch
  (`asyncio.gather` / `_gather` pattern from the SDK internals). Do NOT make a single
  account-wide `get_statistics()` call with no filter.

- **D-02:** Table columns (in order):
  `Name | RequestsServed | BandwidthUsed | BandwidthCached | CacheHitRate | Error%`
  - `Error%` is a computed column: `(Error3xx + Error4xx + Error5xx) / RequestsServed × 100`,
    formatted as a percentage string (e.g. `"0.04%"`). If `RequestsServed` is 0, show `"—"`.
  - `BandwidthUsed` and `BandwidthCached` should be human-formatted (e.g. `"14.2 GB"`)
    using a helper that converts bytes to the appropriate unit.

- **D-03:** `--pull-zone-id <id>` narrows the report to a single zone (one row in the table).
  When provided, skip `iter_pull_zones()` — call `get_statistics(pullZoneId=id)` directly
  and `get_pull_zone(id)` to get the zone name.

- **D-04:** Date range flags — `--from` / `--to` (Typer param names: `from_` / `to_`):
  - Both are optional strings (ISO date, e.g. `"2026-01-01"`).
  - **Default:** CLI computes defaults when omitted:
    - `--to` default: today's date (`date.today().isoformat()`)
    - `--from` default: today minus 7 days (`(date.today() - timedelta(days=7)).isoformat()`)
  - Passed to the API as `dateFrom` / `dateTo` query params respectively.

- **D-05:** Async batch for stats calls — use `asyncio.run(asyncio.gather(...))` in the CLI
  command body, or add a `batch_zone_statistics(zone_ids)` method to `CoreClient` that uses
  `_gather()` internally. Either approach is acceptable; planner should choose the cleaner one
  given existing SDK patterns.

### billing command — design

- **D-06:** `bunnycdn billing` calls `get_billing()` and renders the result as a key-value table
  (Field | Value). Use `output_result()` with curated `columns=` containing the most useful
  billing fields (e.g. `Balance`, `ThisMonthCharges`, `UnpaidInvoicesAmount` — planner should
  check actual API response shape and select meaningful fields).

- **D-07:** No flags on `billing` (no date range, no filters). Single call, single output.

### Both commands — shared patterns

- **D-08:** Both commands register on the root `app` directly (not in a sub-app), same as `purge`.
- **D-09:** Both require `state.api_key`; missing key → actionable error to stderr, exit 1.
- **D-10:** Both use `sdk_errors()` context manager wrapping.
- **D-11:** `--json` flag (top-level, already wired) works on both: stats outputs list of per-zone
  dicts; billing outputs the raw billing dict.

### CliRunner tests

- **D-12:** One test file per command: `tests/cli/test_stats.py`, `tests/cli/test_billing.py`.
- **D-13:** Mock at `CoreClient` boundary (not HTTP), per established TEST-01 pattern.
- **D-14:** Tests cover: success path (exit 0, table output), error path (exit 1, stderr),
  `--json` flag (parseable JSON), missing auth (exit 1).

### README CLI section

- **D-15:** Add a `## CLI` section to the existing `README.md`. Concise reference format:
  - Install snippet (`pip install bunny-cdn-sdk[cli]`)
  - Command groups listed with subcommand summary (one line per group, not per subcommand)
  - Auth env var table: `BUNNY_API_KEY`, `BUNNY_STORAGE_KEY`, `BUNNY_STORAGE_ZONE`,
    `BUNNY_STORAGE_REGION`
  - One `--json | jq` example: `bunnycdn --json pull-zone list | jq '.[] | .Name'`
  - Target: ~60-80 lines, scannable, not exhaustive.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CLI Foundation
- `src/bunny_cdn_sdk/cli/_app.py` — root app, State dataclass, `@app.callback()`; register
  `stats` and `billing` commands here (same as `purge`)
- `src/bunny_cdn_sdk/cli/_output.py` — `output_result()`, `sdk_errors()`, `err_console`
- `src/bunny_cdn_sdk/cli/_pull_zone.py` — reference for top-level command pattern with CoreClient

### SDK Client
- `src/bunny_cdn_sdk/core.py` — `get_statistics(**kwargs)`, `get_billing()`, `iter_pull_zones()`,
  `get_pull_zone(id)`, `_gather()` (async batch internals)

### Tests
- `tests/cli/conftest.py` — `runner` CliRunner fixture
- `tests/cli/test_storage.py` — most recent test file; reference for mock style and assertions

### Requirements
- `.planning/REQUIREMENTS.md` — UTIL-02 and UTIL-03 are the acceptance criteria for this phase

### Documentation
- `README.md` — file to update with `## CLI` section

No external specs or ADRs referenced.

</canonical_refs>

<deferred>
## Deferred Ideas

- `--include-billing` flag on `stats`: merge billing call into stats table. Deferred because
  Bunny's `/billing` endpoint returns account-level totals only — no per-zone cost attribution.
  Revisit in v3.0 if Bunny adds per-zone billing breakdown.

</deferred>

---

*Phase: 12-utility-commands-integration*
*Context gathered: 2026-04-11*
