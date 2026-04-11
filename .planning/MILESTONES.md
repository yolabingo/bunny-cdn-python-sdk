# Milestones

## v1.1 Reliability & Coverage (Shipped: 2026-04-10)

**Phases:** 05–07 (3 phases, 6 plans, 13 tasks)
**Timeline:** 2026-04-10 (1 day)
**Commits:** 33 | **Files changed:** 28 | **Lines:** +4,609 / -30

**Key accomplishments:**

- Coverage gaps closed: `BunnyAPIError.__str__` covered, `_exceptions.py` at 100%; public surface smoke test confirms `CoreClient`, `StorageClient`, `BunnyAPIError` all importable from top-level package
- Context manager lifecycle tests exercise `_client_owner=True` aclose path; dead `list_single_page` removed from `_pagination.py` — `_pagination.py` at 100%
- `RetryTransport` implemented — composable `httpx.AsyncBaseTransport` with 429/5xx/network retry, exponential backoff + full jitter, Retry-After header support; `_retry.py` at 100%
- 22-test MockTransport suite for `RetryTransport` — all retry triggers, backoff math, max-retries exhaustion, composability chain
- `max_retries`/`backoff_base` constructor kwargs wired into `_BaseClient`, `CoreClient`, `StorageClient`; UserWarning on `client=` conflict; `max_retries=0` default preserves v1.0 behavior
- 15 integration tests confirm retry call counts, backward compat, StorageClient parity — 98 tests total, 99% coverage

**Archive:** [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md) | [v1.1-REQUIREMENTS.md](milestones/v1.1-REQUIREMENTS.md)

---

## v1.0 MVP (Shipped: 2026-04-10)

CoreClient (37 methods), StorageClient (4 ops, 10 regions), httpx-based infrastructure, 58-test MockTransport suite (96% coverage)

**Archive:** [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) | [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)

---
