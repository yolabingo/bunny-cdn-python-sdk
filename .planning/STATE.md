---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Release Engineering
status: in_progress
stopped_at: Defining requirements
last_updated: "2026-04-11T00:00:00.000Z"
last_activity: 2026-04-11
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** A Python developer can `pip install bunny-cdn-sdk`, instantiate a client with their API key, and call methods that map 1:1 to Bunny CDN endpoints — no surprises, no hidden behavior.
**Current focus:** v2.1 Release Engineering — CI, Dependabot, version management, TestPyPI publish.

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-11 — Milestone v2.1 started

## Accumulated Context

### Decisions

- [v2.0]: Entry point name is `bunnycdn` (not `bunny`) — PyPI collision with file-watcher package
- [v2.0]: CLI deps go in `[project.optional-dependencies]`, not `[dependency-groups]`
- [v2.0]: DNS record sub-commands included (DZ-05/06/07)
- [v2.0]: Update commands use `--set KEY=VALUE` style
- [v2.0]: Local imports inside command functions prevent circular imports

### Pending Todos

None.

### Blockers/Concerns

- 2 pre-existing `ty` errors in `storage.py` — carried from v1.1, not introduced by v2.0
- CLI Phase 08 ImportError guard untested in clean venv (environment constraint, not code issue)
