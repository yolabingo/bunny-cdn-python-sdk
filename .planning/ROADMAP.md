# Roadmap: bunny-cdn-sdk

**Granularity:** Coarse
**Total Phases:** 3
**Requirements covered:** 9/9

## Milestones

- **[v1.0](milestones/v1.0-ROADMAP.md)** *(archived 2026-04-10)* — CoreClient (37 methods), StorageClient (4 ops, 10 regions), httpx-based infrastructure, 58-test MockTransport suite (96% coverage)

---

## Phase 5: Quality & Coverage

**Goal:** Close all four v1.0 tech-debt coverage gaps so every existing module reaches 100% and the public package surface has a smoke test.

**Plans:** 0/2 plans complete

Plans:
- [ ] 05-01-PLAN.md — Exception `__str__` test + public surface smoke test
- [ ] 05-02-PLAN.md — Context manager lifecycle tests + `list_single_page` cleanup

**Requirements:**
- QUAL-01, QUAL-02, QUAL-03, QUAL-04

**Success Criteria:**
- [ ] `_exceptions.py` coverage is 100% — `BunnyAPIError.__str__` branch exercised by at least one test
- [ ] `_client.py` coverage is 100% — both async and sync context manager exit paths exercised
- [ ] `list_single_page` is removed from `_pagination.py` or wired to at least one `core.py` method — no orphaned export
- [ ] At least one test imports `CoreClient`, `StorageClient`, and `BunnyAPIError` from `bunny_cdn_sdk` (top-level) and all resolve without error
- [ ] `uv run pytest --cov=src` exits 0 with all pre-existing modules at 100%

---

## Phase 6: RetryTransport

**Goal:** Implement a standalone, composable `RetryTransport` httpx transport with exponential backoff + jitter, covering 429/5xx/network retry triggers.

**Plans:** 0/2 plans complete

Plans:
- [ ] 06-01-PLAN.md — Implement `_retry.py` (`RetryTransport` class) and export from `__init__.py`
- [ ] 06-02-PLAN.md — MockTransport-backed tests for all retry triggers, backoff growth, and composability

**Requirements:**
- RETRY-01, RETRY-02, RETRY-03, RETRY-05

**Success Criteria:**
- [ ] `from bunny_cdn_sdk import RetryTransport` resolves without error
- [ ] `RetryTransport` retries on 429 (respects `Retry-After` if present), 5xx, `httpx.ConnectError`, and `httpx.TimeoutException` — all four triggers covered by tests
- [ ] Backoff with jitter is confirmed by patching `asyncio.sleep` and asserting monotonically increasing delay sequence
- [ ] User can construct `RetryTransport` independently and pass it as `transport=` to `httpx.AsyncClient`, then inject via `client=` kwarg — integration test confirms correct routing
- [ ] `uv run pytest` exits 0; `_retry.py` coverage is 100%

---

## Phase 7: Constructor Integration

**Goal:** Wire `max_retries` and `backoff_base` kwargs into `CoreClient` and `StorageClient` constructors, with `max_retries=0` (default) preserving exact v1.0 behaviour.

**Plans:** 0/2 plans complete

Plans:
- [ ] 07-01-PLAN.md — Add `max_retries`/`backoff_base` kwargs to `_BaseClient`, `CoreClient`, and `StorageClient`
- [ ] 07-02-PLAN.md — Integration tests confirming retry counts, backward compat (zero retries), and no regressions in existing test suite

**Requirements:**
- RETRY-04

**Success Criteria:**
- [ ] `CoreClient(api_key, max_retries=3)` and `StorageClient(zone, password, max_retries=3, backoff_base=1.0)` accepted without error
- [ ] `CoreClient(api_key)` with 500-returning MockTransport produces exactly 1 HTTP call (no retry) — v1.0 parity confirmed
- [ ] `CoreClient(api_key, max_retries=2)` with 500-returning MockTransport produces exactly 3 HTTP calls (1 + 2 retries)
- [ ] Existing `test_core.py` and `test_storage.py` suites pass unchanged — no regressions
- [ ] All 9 v1.1 requirements (QUAL-01..04, RETRY-01..05) marked passing; `uv run pytest --cov=src` exits 0
