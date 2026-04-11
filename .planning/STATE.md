---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Stream API
status: planning
last_updated: "2026-04-10T00:00:00Z"
last_activity: 2026-04-10
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Current Status

**Milestone:** v2.0 — Typer CLI
**Status:** Defining requirements
**Last activity:** 2026-04-10 — Milestone v2.0 started

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-10 after v1.1 milestone)

**Core value:** A Python developer can `pip install bunny-cdn-sdk`, instantiate a client with their API key, and call methods that map 1:1 to Bunny CDN endpoints — no surprises, no hidden behavior.

## Accumulated Context (from v1.1)

- `_client.py` lines 121-122 uncovered — bare `except Exception` on JSON parse failure in error extraction (low-risk, needs malformed-body test)
- `test_public_surface.py` does not explicitly assert `RetryTransport` — add in next cleanup cycle
- 2 pre-existing `ty` errors in `storage.py` (`call-non-callable`, `invalid-type-form`) — not introduced by v1.1
- 59 pre-existing ruff violations (PLR2004, ANN401, TRY003) — not introduced by v1.1
- `client=` is keyword-only on CoreClient and StorageClient as of v1.1
