---
phase: 10-coreclient-sub-apps
plan: "05"
subsystem: cli-tests
tags: [tests, cli, pull-zone, storage-zone, typer, runner]
dependency_graph:
  requires: ["10-04"]
  provides: ["tests/cli/test_pull_zone.py", "tests/cli/test_storage_zone.py"]
  affects: ["ci", "test-suite"]
tech_stack:
  added: []
  patterns: ["CliRunner", "patch(bunny_cdn_sdk.core.CoreClient)", "mock-at-boundary"]
key_files:
  created:
    - tests/cli/test_pull_zone.py
    - tests/cli/test_storage_zone.py
  modified: []
decisions: []
metrics:
  duration: "2 minutes"
  completed: "2026-04-11"
  tasks_completed: 2
  files_changed: 2
requirements:
  - PZ-01
  - PZ-02
  - PZ-03
  - PZ-04
  - PZ-05
  - PZ-06
  - SZ-01
  - SZ-02
  - SZ-03
  - SZ-04
  - SZ-05
  - TEST-01
  - TEST-02
  - TEST-03
---

# Phase 10 Plan 05: CLI Tests for Pull Zone and Storage Zone Summary

CliRunner-based tests for all pull-zone (6 commands, 20 tests) and storage-zone (5 commands, 19 tests) commands, mocking at the CoreClient boundary — all 168 tests pass with no regressions.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write tests for pull-zone commands | d28b11a | tests/cli/test_pull_zone.py |
| 2 | Write tests for storage-zone commands | 317b7d9 | tests/cli/test_storage_zone.py |

## What Was Built

### tests/cli/test_pull_zone.py (20 tests)

Covers all 6 pull-zone commands:
- **list**: success (exit 0, "my-zone" in output), error (BunnyAuthenticationError → exit 1), JSON (parseable list), missing auth (exit 1)
- **get**: success, not-found error, JSON (dict with "Id" key)
- **create**: success ("new-zone" in output), error (BunnyAPIError), JSON (dict)
- **delete**: with --yes (exit 0, "Deleted pull zone 1"), prompt confirmed (y\n), prompt aborted (n\n, exit != 0), not-found error
- **purge**: success ("Purged cache"), not-found error
- **update**: success with diff (OriginUrl in output), JSON mode, malformed --set (exit 1), error on get

### tests/cli/test_storage_zone.py (19 tests)

Covers all 5 storage-zone commands:
- **list**: success ("my-storage" in output), error (BunnyAuthenticationError), JSON, missing auth
- **get**: success, not-found error, JSON
- **create**: success, error (BunnyAPIError), JSON
- **delete**: with --yes ("Deleted storage zone 2"), prompt confirmed, prompt aborted, not-found error
- **update**: success with diff (Region in output), JSON mode, malformed --set, error on get, no-fields-changed edge case

## Mock Strategy

All tests use `patch("bunny_cdn_sdk.core.CoreClient")` — patching at the module-level location where the class is defined, not where it is imported. This is the reliable pattern confirmed in Phase 09.

Each test uses a `with patch(...)` context manager to scope patches, preventing cross-test leakage.

## Verification Results

```
tests/cli/test_pull_zone.py: 20 passed
tests/cli/test_storage_zone.py: 19 passed
tests/cli/ (full CLI suite): 70 passed
tests/ (full suite): 168 passed
```

No regressions from plans 01-04.

## Requirements Satisfied

| Requirement | Coverage |
|-------------|----------|
| TEST-01 | All mocks at CoreClient boundary, not HTTP level |
| TEST-02 | Success (exit 0) and error (exit 1) paths tested per command |
| TEST-03 | --json flag tested per command, output verified as parseable JSON |
| PZ-01 through PZ-06 | All pull-zone command paths exercised |
| SZ-01 through SZ-05 | All storage-zone command paths exercised |

## Deviations from Plan

None — plan executed exactly as written. The test structure, fixtures, and mock patterns matched the plan's action sections without modification.

## Known Stubs

None. Both test files are fully wired — no placeholder data flows to untested paths.

## Threat Flags

None. Tests use literal `"k"` strings as API keys (not real credentials), and each test scopes its own patch context to prevent mock leakage between tests (matches T-10-16 and T-10-17 dispositions).

## Self-Check: PASSED

- tests/cli/test_pull_zone.py: EXISTS
- tests/cli/test_storage_zone.py: EXISTS
- Commit d28b11a: EXISTS (test_pull_zone.py)
- Commit 317b7d9: EXISTS (test_storage_zone.py)
- 168 tests pass: CONFIRMED
