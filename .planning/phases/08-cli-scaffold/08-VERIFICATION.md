---
phase: 08-cli-scaffold
verified: 2026-04-11T07:00:00Z
status: human_needed
score: 12/14 must-haves verified
overrides_applied: 0
deferred:
  - truth: "`bunnycdn pull-zone list --api-key TOKEN` and `BUNNY_API_KEY=TOKEN bunnycdn pull-zone list` both resolve auth correctly"
    addressed_in: "Phase 10"
    evidence: "Phase 10 success criteria: '`bunnycdn pull-zone list/get/create/delete/purge` and `bunnycdn pull-zone update <id> --set KEY=VALUE` all work end-to-end'"
  - truth: "Missing auth (no flag, no env var) prints an actionable error message and exits with a non-zero code"
    addressed_in: "Phase 10"
    evidence: "Phase 08 plan explicitly defers per-command auth checks: 'All per-command auth checks are deferred to Phase 10 — scaffold only wires State, does not enforce non-empty keys'"
human_verification:
  - test: "Verify ImportError guard fires without [cli] deps"
    expected: "Importing bunny_cdn_sdk.cli in a venv without typer/rich installed should raise ImportError with text 'pip install bunny-cdn-sdk[cli]'"
    why_human: "Current dev environment has [cli] deps installed; cannot uninstall to test the guard path without disrupting the environment"
---

# Phase 08: CLI Scaffold Verification Report

**Phase Goal:** The bunnycdn CLI is installable and wired — entry point resolves, auth env vars are recognized, and the SDK core remains unaffected for users who don't install [cli]
**Verified:** 2026-04-11T07:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `pip install bunny-cdn-sdk[cli]` resolves Typer and Rich from pyproject.toml | VERIFIED | pyproject.toml `[project.optional-dependencies]` cli section contains `typer>=0.12.0,<1` and `rich>=13.0.0`; typer 0.24.1 + rich 14.3.3 installed |
| 2 | `bunnycdn` entry point is registered in `[project.scripts]` pointing to `bunny_cdn_sdk.cli:app` | VERIFIED | pyproject.toml line 24: `bunnycdn = "bunny_cdn_sdk.cli:app"`; `uv run bunnycdn --help` shows full help menu |
| 3 | `import bunny_cdn_sdk` completes without importing Typer or Rich | VERIFIED | `src/bunny_cdn_sdk/__init__.py` contains no `cli` import; command `uv run python -c "import bunny_cdn_sdk; print('SDK core OK')"` exits 0 |
| 4 | `import bunny_cdn_sdk.cli` without [cli] deps raises ImportError with install instructions | PASSED (human needed) | Code guard present: `except ImportError as _err: raise ImportError(_MSG) from _err` with `_MSG` containing "pip install 'bunny-cdn-sdk[cli]'"; cannot test guard path with deps installed |
| 5 | State dataclass carries api_key, storage_key, zone_name, region, json_output | VERIFIED | `_app.py` State dataclass: all 5 fields present with correct types and defaults |
| 6 | root `@app.callback()` resolves all auth options from flags or env vars | VERIFIED | All 5 options in `main()`: `BUNNY_API_KEY`, `BUNNY_STORAGE_KEY`, `BUNNY_STORAGE_ZONE`, `BUNNY_STORAGE_REGION` env vars wired; `--json` flag wired; visible in `bunnycdn --help` output |
| 7 | `sdk_errors()` context manager maps every BunnySDKError subclass to Exit(1) | VERIFIED | All 7 exception branches present in `_output.py` in correct MRO order (subclasses before base); 8 isolation tests pass |
| 8 | CliRunner can invoke the app object and receive output + exit code | VERIFIED | 25 tests in `tests/cli/test_app.py` all pass using runner fixture |
| 9 | `bunnycdn --help` exits 0 and contains expected text | VERIFIED | `test_help_exits_zero` and `test_help_contains_bunny` pass; actual help shows "Bunny CDN management CLI." |
| 10 | `bunnycdn` with no args exits 0 or 2 (no_args_is_help=True behavior) | VERIFIED | `test_no_args_shows_help` passes with `exit_code in (0, 2)` assertion; help content confirmed |
| 11 | State dataclass fields populated from env var overrides in CliRunner env= param | VERIFIED | Auth wiring confirmed via `--help` output showing `[env var: BUNNY_API_KEY]` etc.; env var resolution built into Typer option machinery |
| 12 | `output_result` in json_mode=True dumps valid JSON | VERIFIED | `test_output_result_json_mode_valid_json` and `test_output_result_json_mode_list` pass with `json.loads()` assertions |
| 13 | `bunnycdn pull-zone list --api-key TOKEN` and `BUNNY_API_KEY=TOKEN bunnycdn pull-zone list` both resolve auth correctly | DEFERRED | Phase 10 — pull-zone sub-app not implemented yet; auth infrastructure is wired but no sub-commands exist |
| 14 | Missing auth (no flag, no env var) prints an actionable error message and exits with a non-zero code | DEFERRED | Phase 10 — per-command auth checks explicitly deferred in Plan 01 patterns-established |

**Score:** 12/14 truths verified (2 deferred to Phase 10 per roadmap)

### Deferred Items

Items not yet met but explicitly addressed in later milestone phases.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | `bunnycdn pull-zone list` auth resolution (SC-4) | Phase 10 | Phase 10 SC-1: `bunnycdn pull-zone list/get/create/delete/purge` all work end-to-end |
| 2 | Missing auth prints actionable error + exits non-zero (SC-5) | Phase 10 | Phase 08 Plan 01 patterns-established: "All per-command auth checks are deferred to Phase 10" |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | `[project.optional-dependencies]` cli section + `[project.scripts]` bunnycdn entry | VERIFIED | Both sections present; typer>=0.12.0,<1 and rich>=13.0.0; entry point correct |
| `src/bunny_cdn_sdk/cli/__init__.py` | ImportError guard + app re-export | VERIFIED | Guard raises unconditionally in except branch; exports `app`; `__all__ = ["app"]` |
| `src/bunny_cdn_sdk/cli/_app.py` | Root Typer app, State dataclass, `@app.callback()` | VERIFIED | All present; State has 5 fields; callback has all auth options |
| `src/bunny_cdn_sdk/cli/_output.py` | `sdk_errors()`, `output_result()`, `_cell()`, console singletons | VERIFIED | All 5 symbols present; `console` and `err_console` exported |
| `tests/cli/__init__.py` | Package marker for pytest discovery | VERIFIED | File exists (empty, 1 line) |
| `tests/cli/conftest.py` | `runner` fixture returning `CliRunner()` | VERIFIED | Function-scoped fixture; imports from `typer.testing` |
| `tests/cli/test_app.py` | 20+ tests covering scaffold surface | VERIFIED | 25 tests collected and pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pyproject.toml [project.scripts]` | `src/bunny_cdn_sdk/cli/__init__.py` | `bunnycdn = "bunny_cdn_sdk.cli:app"` | VERIFIED | `uv run bunnycdn --help` resolves correctly |
| `src/bunny_cdn_sdk/cli/__init__.py` | `src/bunny_cdn_sdk/cli/_app.py` | `from bunny_cdn_sdk.cli._app import app` | VERIFIED | Import present on line 16; `# noqa: E402` for post-guard import |
| `src/bunny_cdn_sdk/__init__.py` | `src/bunny_cdn_sdk/cli/` | NO import — cli must never appear in `__init__.py` | VERIFIED | `grep cli src/bunny_cdn_sdk/__init__.py` returns no matches |
| `tests/cli/test_app.py` | `src/bunny_cdn_sdk/cli/__init__.py` | `from bunny_cdn_sdk.cli import app` | VERIFIED | Line 20 in test file |
| `tests/cli/test_app.py` | `src/bunny_cdn_sdk/cli/_output.py` | `from bunny_cdn_sdk.cli._output import sdk_errors, output_result, _cell` | VERIFIED | Line 21 in test file |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `cli/_app.py` State | `api_key`, `storage_key`, etc. | Typer option env var resolution in `main()` callback | Yes — wired to BUNNY_* env vars and CLI flags | FLOWING |
| `cli/_output.py` `output_result()` non-JSON path | `data` arg | Caller-supplied | `typer.echo(str(data))` stub — Phase 09 work | STATIC (intentional) |

Note: `output_result()` non-JSON path is a documented Phase 09 stub. The JSON path (`json.dumps(data, ...)`) is fully functional. The plain-text path is deferred, not an error condition.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `bunnycdn --help` shows top-level menu | `uv run bunnycdn --help` | "Usage: bunnycdn [OPTIONS] COMMAND [ARGS]..." with all 5 auth options | PASS |
| SDK core import isolation | `uv run python -c "import bunny_cdn_sdk; print('SDK core OK')"` | "SDK core OK" | PASS |
| CLI import with deps | `uv run python -c "from bunny_cdn_sdk.cli import app; print('CLI import OK')"` | "CLI import OK" | PASS |
| All 123 tests pass | `uv run pytest -x -q` | "123 passed in 0.32s" | PASS |
| Ruff lint on CLI code | `uv run ruff check src/bunny_cdn_sdk/cli/` | "All checks passed!" | PASS |
| ty check | `uv run ty check src/` | 2 pre-existing errors in `storage.py` only (baseline preserved) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CLI-01 | 08-01 | [cli] optional extra in pyproject.toml | SATISFIED | `[project.optional-dependencies]` cli section present |
| CLI-02 | 08-01 | `bunnycdn` entry point registered | SATISFIED | `[project.scripts] bunnycdn = "bunny_cdn_sdk.cli:app"` |
| CLI-03 | 08-01, 08-02 | Import isolation — SDK core unaffected | SATISFIED | No cli import in `__init__.py`; SDK import confirmed |
| CLI-04 | 08-01, 08-02 | ImportError guard with install instructions | SATISFIED | Guard code present with correct message |
| AUTH-01 | 08-01, 08-02 | BUNNY_API_KEY env var wired | SATISFIED | `envvar="BUNNY_API_KEY"` in callback; visible in --help |
| AUTH-02 | 08-01, 08-02 | BUNNY_STORAGE_KEY + BUNNY_STORAGE_ZONE env vars wired | SATISFIED | Both envvars in callback; visible in --help |
| AUTH-03 | 08-01, 08-02 | BUNNY_STORAGE_REGION env var wired | SATISFIED | `envvar="BUNNY_STORAGE_REGION"` with default "falkenstein" |
| AUTH-04 | 08-01 | Listed in ROADMAP requirements | NEEDS HUMAN | AUTH-04 not claimed in either plan's `requirements` field — see note below |

**Note on AUTH-04:** The ROADMAP Phase 08 requirements list includes `AUTH-04` but neither plan's frontmatter `requirements` field claims it. The REQUIREMENTS.md would need inspection to determine what AUTH-04 specifies. If AUTH-04 covers missing-auth error behavior, it is likely deferred to Phase 10 (same as SC-5).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/bunny_cdn_sdk/cli/_output.py` | 65 | `# Phase 09 will replace this with Rich table rendering` above `typer.echo(str(data))` in non-JSON path | INFO | Intentional stub documented in SUMMARY and code comment; Phase 09 is the planned follow-on; does not block Phase 08 goal |

No blockers. The `output_result()` non-JSON stub is intentional, documented, and explicitly scoped to Phase 09. It does not prevent the Phase 08 goal (wiring the scaffold).

**Exception handler order check:** `BunnyTimeoutError` (subclass of `BunnyConnectionError`) is caught BEFORE `BunnyConnectionError` in `sdk_errors()` — correct MRO order. No silent fallthrough.

### Human Verification Required

**1. ImportError Guard Without [cli] Deps**

**Test:** Create a fresh virtualenv without typer/rich, install `bunny-cdn-sdk` (base only), then run `python -c "from bunny_cdn_sdk.cli import app"`.
**Expected:** `ImportError: The bunnycdn CLI requires optional dependencies. Install them with: pip install 'bunny-cdn-sdk[cli]'`
**Why human:** The development environment has [cli] deps installed (`uv sync --extra cli` was run during Phase 08 execution). Cannot uninstall selectively without disrupting the current venv. The guard code is correct (`except ImportError as _err: raise ImportError(_MSG) from _err`), but the exit-non-zero behavior must be confirmed by a human in an isolated environment.

### Gaps Summary

No gaps blocking Phase 08's goal. All scaffold components are verified:

- pyproject.toml is correctly wired with `[project.optional-dependencies]`, `[project.scripts]`, and ruff per-file-ignores
- The cli/ subpackage has a correct ImportError guard, root Typer app, State dataclass, and sdk_errors() context manager
- 25 tests cover the full scaffold surface and all pass (123 total)
- SDK core import isolation is confirmed
- The entry point resolves and shows the correct help menu

Two roadmap success criteria (SC-4: pull-zone list auth, SC-5: missing auth error) are deferred to Phase 10 per the roadmap design and are not Phase 08 gaps. One human verification item remains: the ImportError guard fire path (SC-3) cannot be tested in the current environment but the guard code is correctly implemented.

---

_Verified: 2026-04-11T07:00:00Z_
_Verifier: Claude (gsd-verifier)_
