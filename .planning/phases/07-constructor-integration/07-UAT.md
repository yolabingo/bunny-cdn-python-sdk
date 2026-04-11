---
status: complete
phase: 07-constructor-integration
source: 07-01-SUMMARY.md, 07-02-SUMMARY.md
started: 2026-04-10T00:00:00Z
updated: 2026-04-10T00:00:00Z
---

## Current Test

## Current Test

[testing complete]

## Tests

### 1. Full test suite passes — 98 tests
expected: Run `uv run pytest tests/ -x -q` → exits 0 with 98 tests passed (83 pre-existing + 15 new constructor retry tests). No failures or errors.
result: pass

### 2. _retry.py coverage at 100%
expected: Run `uv run pytest --cov=src --cov-report=term-missing tests/` → the `_retry.py` line shows `100%` in the coverage table. No missing lines.
result: pass

### 3. Default CoreClient — no RetryTransport
expected: In a Python REPL (`uv run python`): `from bunny_cdn_sdk import CoreClient; import httpx; c = CoreClient("key"); print(type(c._client._transport))` → output shows a plain httpx transport type (NOT `RetryTransport`). No error on construction.
result: pass

### 4. CoreClient with max_retries wires RetryTransport
expected: In a Python REPL: `from bunny_cdn_sdk import CoreClient, RetryTransport; c = CoreClient("key", max_retries=3); print(isinstance(c._client._transport, RetryTransport))` → prints `True`. No error on construction.
result: pass

### 5. StorageClient with max_retries wires RetryTransport
expected: In a Python REPL: `from bunny_cdn_sdk import StorageClient, RetryTransport; c = StorageClient("zone", "pwd", max_retries=3); print(isinstance(c._client._transport, RetryTransport))` → prints `True`. No error on construction.
result: pass

### 6. Conflict: client= + max_retries>0 emits UserWarning
expected: In a Python REPL with `warnings.catch_warnings(record=True)`: `CoreClient("key", client=httpx.AsyncClient(), max_retries=1)` → exactly one `UserWarning` emitted, no exception raised. Message mentions the conflict.
result: pass

### 7. Backward compat — max_retries=0 → exactly 1 HTTP call
expected: `uv run pytest tests/test_constructor_retry.py -v -k "backward"` → the backward-compat tests pass. Confirms max_retries=0 (default) produces exactly 1 HTTP call against an always-500 mock (no retry).
result: pass

### 8. Retry call count — max_retries=2 → 3 total HTTP calls
expected: `uv run pytest tests/test_constructor_retry.py -v -k "max_retries"` → passes. Confirms CoreClient with max_retries=2 and always-500 transport produces exactly 3 HTTP calls (1 original + 2 retries).
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
