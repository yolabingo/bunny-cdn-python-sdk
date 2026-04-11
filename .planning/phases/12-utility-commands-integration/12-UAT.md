---
status: complete
phase: 12-utility-commands-integration
source: 12-01-SUMMARY.md, 12-02-SUMMARY.md
started: 2026-04-11T17:40:00Z
updated: 2026-04-11T17:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. stats and billing appear in root help
expected: Running `bunnycdn --help` shows `stats` and `billing` listed as commands alongside pull-zone, storage-zone, etc.
result: pass

### 2. stats --help shows expected flags
expected: `bunnycdn stats --help` shows three optional flags: `--pull-zone-id`, `--from`, and `--to` (no required arguments)
result: pass

### 3. stats missing auth guard
expected: `bunnycdn stats` with no `BUNNY_API_KEY` env var and no `--api-key` flag prints a clear error to stderr and exits non-zero (no Python traceback)
result: pass

### 4. billing missing auth guard
expected: `bunnycdn billing` with no `BUNNY_API_KEY` set prints a clear error to stderr and exits non-zero (no Python traceback)
result: pass

### 5. stats --json output
expected: `bunnycdn --api-key k --json stats` (or with env var set) returns valid JSON — either a list of zone-stats objects or an error message on stderr; no raw Python exception in stdout
result: pass

### 6. billing --json output
expected: `bunnycdn --api-key k --json billing` returns valid JSON dict — either billing data or an auth error on stderr; no raw Python exception in stdout
result: pass

### 7. README CLI section
expected: Opening README.md shows a `## CLI` section containing: install snippet (`pip install "bunny-cdn-sdk[cli]"`), a command groups table listing at least `stats` and `billing`, an env var table with `BUNNY_API_KEY`, and a `--json | jq` example
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
