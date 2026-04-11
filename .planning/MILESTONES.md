# Milestones

## v2.0 Typer CLI (Shipped: 2026-04-11)

**Phases:** 08–12 (5 phases, 13 plans, 62 commits)
**Timeline:** 2026-04-11 (1 day)

**Key accomplishments:**

- Optional `[cli]` extra with Typer + Rich — `bunnycdn` entry point, ImportError guard, typed State dataclass, sdk_errors() context manager; zero impact on SDK core import
- Rich table output by default, `--json` flag for machine-readable output, auth guard with actionable errors on all commands
- 4 CoreClient resource groups: pull-zone (6 cmds), storage-zone (5 cmds), dns-zone (4 cmds + nested record sub-commands), video-library (5 cmds)
- StorageClient sub-app with separate auth wiring — zone/key/region env vars; list/upload/download/delete commands
- `bunnycdn stats` and `bunnycdn billing` utility commands with concurrent asyncio.gather for per-zone statistics
- README CLI section, 241 tests passing (110 CliRunner tests covering success, error, and --json paths)

**Archive:** [v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md) | [v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md)

---

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
