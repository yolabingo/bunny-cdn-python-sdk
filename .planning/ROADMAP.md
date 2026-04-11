# Roadmap: bunny-cdn-sdk

## Milestones

- ✅ **[v1.0 MVP](milestones/v1.0-ROADMAP.md)** *(shipped 2026-04-10)* — CoreClient (37 methods), StorageClient (4 ops, 10 regions), httpx infrastructure, 58-test suite (96% coverage)
- ✅ **[v1.1 Reliability & Coverage](milestones/v1.1-ROADMAP.md)** *(shipped 2026-04-10)* — RetryTransport, constructor retry kwargs, coverage gaps closed, 98 tests (99% coverage)
- ✅ **[v2.0 Typer CLI](milestones/v2.0-ROADMAP.md)** *(shipped 2026-04-11)* — Optional [cli] extra with 5 sub-command groups, 47 requirements, 241 tests

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 01–04) — SHIPPED 2026-04-10</summary>

- [x] Phase 01: Package Scaffold & Exception Hierarchy (2/2 plans)
- [x] Phase 02: Base Client Infrastructure (2/2 plans)
- [x] Phase 03: Core & Storage API Clients (2/2 plans)
- [x] Phase 04: Test Suite (2/2 plans)

</details>

<details>
<summary>✅ v1.1 Reliability & Coverage (Phases 05–07) — SHIPPED 2026-04-10</summary>

- [x] Phase 05: Quality & Coverage (2/2 plans) — coverage gaps, public surface smoke test
- [x] Phase 06: RetryTransport (2/2 plans) — composable retry transport, 100% _retry.py coverage
- [x] Phase 07: Constructor Integration (2/2 plans) — max_retries/backoff_base kwargs, 15 integration tests

</details>

<details>
<summary>✅ v2.0 Typer CLI (Phases 08–12) — SHIPPED 2026-04-11</summary>

- [x] Phase 08: CLI Scaffold (2/2 plans) — [cli] extra, bunnycdn entry point, ImportError guard, State, sdk_errors()
- [x] Phase 09: Output Layer & Error Handling (1/1 plans) — Rich table rendering, --json flag, stderr error output
- [x] Phase 10: CoreClient Sub-Apps (6/6 plans) — pull-zone, storage-zone, dns-zone (with nested record), video-library; 110+ CliRunner tests
- [x] Phase 11: StorageClient Sub-App (2/2 plans) — storage list/upload/download/delete with separate auth wiring
- [x] Phase 12: Utility Commands & Integration (2/2 plans) — stats, billing, README CLI section; 241 tests total

</details>

## Progress

**Next milestone:** run `/gsd-new-milestone` to define v3.0 scope.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 01. Package Scaffold & Exception Hierarchy | v1.0 | 2/2 | Complete | 2026-04-10 |
| 02. Base Client Infrastructure | v1.0 | 2/2 | Complete | 2026-04-10 |
| 03. Core & Storage API Clients | v1.0 | 2/2 | Complete | 2026-04-10 |
| 04. Test Suite | v1.0 | 2/2 | Complete | 2026-04-10 |
| 05. Quality & Coverage | v1.1 | 2/2 | Complete | 2026-04-10 |
| 06. RetryTransport | v1.1 | 2/2 | Complete | 2026-04-10 |
| 07. Constructor Integration | v1.1 | 2/2 | Complete | 2026-04-10 |
| 08. CLI Scaffold | v2.0 | 2/2 | Complete | 2026-04-11 |
| 09. Output Layer & Error Handling | v2.0 | 1/1 | Complete | 2026-04-11 |
| 10. CoreClient Sub-Apps | v2.0 | 6/6 | Complete | 2026-04-11 |
| 11. StorageClient Sub-App | v2.0 | 2/2 | Complete | 2026-04-11 |
| 12. Utility Commands & Integration | v2.0 | 2/2 | Complete | 2026-04-11 |

---

*See [MILESTONES.md](MILESTONES.md) for shipped milestone details.*
