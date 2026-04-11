# Roadmap: bunny-cdn-sdk

## Milestones

- ✅ **[v1.0 MVP](milestones/v1.0-ROADMAP.md)** *(shipped 2026-04-10)* — CoreClient (37 methods), StorageClient (4 ops, 10 regions), httpx infrastructure, 58-test suite (96% coverage)
- ✅ **[v1.1 Reliability & Coverage](milestones/v1.1-ROADMAP.md)** *(shipped 2026-04-10)* — RetryTransport, constructor retry kwargs, coverage gaps closed, 98 tests (99% coverage)
- 📋 **v2.0 Stream API** *(planned)* — StreamClient (Videos + Collections CRUD), pagination, extended coverage

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

### 📋 v2.0 Stream API (Planned)

*(To be defined via `/gsd-new-milestone`)*

---

*See [MILESTONES.md](MILESTONES.md) for shipped milestone details.*
