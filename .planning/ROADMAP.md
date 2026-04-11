# Roadmap: bunny-cdn-sdk

## Milestones

- ✅ **[v1.0 MVP](milestones/v1.0-ROADMAP.md)** *(shipped 2026-04-10)* — CoreClient (37 methods), StorageClient (4 ops, 10 regions), httpx infrastructure, 58-test suite (96% coverage)
- ✅ **[v1.1 Reliability & Coverage](milestones/v1.1-ROADMAP.md)** *(shipped 2026-04-10)* — RetryTransport, constructor retry kwargs, coverage gaps closed, 98 tests (99% coverage)
- 🚧 **v2.0 Typer CLI** — Phases 08–12 (in progress)

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

### 🚧 v2.0 Typer CLI (In Progress)

**Milestone Goal:** Add an optional Typer-based CLI (`pip install bunny-cdn-sdk[cli]`) wrapping Core and Storage clients with Rich table output and `--json` flag support.

- [x] **Phase 08: CLI Scaffold** - pyproject.toml [cli] extra, bunnycdn entry point, cli/ subpackage, ImportError guard, State dataclass, auth wiring (completed 2026-04-11)
- [ ] **Phase 09: Output Layer & Error Handling** - sdk_errors() context manager, output_result(), Rich table renderer, _cell() helper, full unit tests
- [ ] **Phase 10: CoreClient Sub-Apps** - pull-zone, storage-zone, dns-zone (including record sub-commands), video-library commands with update support; CliRunner tests
- [ ] **Phase 11: StorageClient Sub-App** - storage list/upload/download/delete with separate auth wiring; CliRunner tests
- [ ] **Phase 12: Utility Commands & Integration** - stats, billing, integration test suite, README CLI section

## Phase Details

### Phase 08: CLI Scaffold
**Goal**: The bunnycdn CLI is installable and wired — entry point resolves, auth env vars are recognized, and the SDK core remains unaffected for users who don't install [cli]
**Depends on**: Phase 07
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Success Criteria** (what must be TRUE):
  1. `pip install bunny-cdn-sdk[cli]` succeeds and `bunnycdn --help` shows the top-level help menu
  2. `python -c "import bunny_cdn_sdk"` completes without importing Typer or Rich in a base-only environment
  3. Running `bunnycdn` without [cli] deps installed prints a clear "install bunny-cdn-sdk[cli]" message and exits non-zero
  4. `bunnycdn pull-zone list --api-key TOKEN` and `BUNNY_API_KEY=TOKEN bunnycdn pull-zone list` both resolve auth correctly
  5. Missing auth (no flag, no env var) prints an actionable error message and exits with a non-zero code
**Plans**: 2 plans
Plans:
- [x] 08-01-PLAN.md — pyproject.toml [cli] extra, entry point, cli/ subpackage source files (ImportError guard, State, sdk_errors)
- [x] 08-02-PLAN.md — tests/cli/ package with CliRunner fixture and scaffold-level tests
**UI hint**: yes

### Phase 09: Output Layer & Error Handling
**Goal**: Every CLI command has a correct, tested output and error infrastructure — Rich tables on success, stderr messages on failure, deterministic exit codes, JSON fallback
**Depends on**: Phase 08
**Requirements**: OUT-01, OUT-02, OUT-03, OUT-04, OUT-05, OUT-06
**Success Criteria** (what must be TRUE):
  1. Any command that returns a list renders a Rich table with curated columns (not raw dict dumps) when `--json` is not passed
  2. Any command that returns a single resource renders a Rich table (single-row or key-value format)
  3. `--json` on any command outputs valid, parseable JSON to stdout (lists collect all pages before printing)
  4. All SDK and auth errors print to stderr (not stdout) and exit with code 1; success exits with code 0
  5. JSON serialization never crashes on non-serializable API field values (datetime, UUID, etc.)
**Plans**: 1 plan
Plans:
- [ ] 09-01-PLAN.md — Rich table rendering in output_result() + columns param + 6 table-rendering tests
**UI hint**: yes

### Phase 10: CoreClient Sub-Apps
**Goal**: All CoreClient resource groups are accessible from the CLI — pull zones, storage zones, DNS zones (including record sub-commands), and video libraries — with full CRUD plus update commands
**Depends on**: Phase 09
**Requirements**: PZ-01, PZ-02, PZ-03, PZ-04, PZ-05, PZ-06, SZ-01, SZ-02, SZ-03, SZ-04, SZ-05, DZ-01, DZ-02, DZ-03, DZ-04, DZ-05, DZ-06, DZ-07, VL-01, VL-02, VL-03, VL-04, VL-05, UTIL-01, TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. `bunnycdn pull-zone list/get/create/delete/purge` and `bunnycdn pull-zone update <id> --set KEY=VALUE` all work end-to-end
  2. `bunnycdn storage-zone list/get/create/delete` and `bunnycdn storage-zone update <id> --set KEY=VALUE` all work end-to-end
  3. `bunnycdn dns-zone list/get/create/delete` work, and `bunnycdn dns-zone record add/update/delete` manage DNS records
  4. `bunnycdn video-library list/get/create/delete` and `bunnycdn video-library update <id> --set KEY=VALUE` all work end-to-end
  5. `bunnycdn purge <url>` purges a URL; all delete commands prompt for confirmation; all commands have passing CliRunner tests covering success path, error path, and `--json` flag
**Plans**: TBD
**UI hint**: yes

### Phase 11: StorageClient Sub-App
**Goal**: Storage file operations are accessible via CLI with correct separate auth wiring — zone name, storage key, and region are all configurable via flags or env vars
**Depends on**: Phase 10
**Requirements**: ST-01, ST-02, ST-03, ST-04
**Success Criteria** (what must be TRUE):
  1. `bunnycdn storage list [path]` lists storage files using `BUNNY_STORAGE_ZONE` + `BUNNY_STORAGE_KEY` + `BUNNY_STORAGE_REGION` env vars (region defaults to `falkenstein`)
  2. `bunnycdn storage upload <local-path> <remote-path>` uploads a local file to the specified storage path
  3. `bunnycdn storage download <remote-path> <local-path>` downloads a storage file to the local filesystem
  4. `bunnycdn storage delete <remote-path>` prompts for confirmation and deletes the remote file; all four commands have passing CliRunner tests
**Plans**: TBD
**UI hint**: yes

### Phase 12: Utility Commands & Integration
**Goal**: The CLI is complete — stats and billing commands work, the full command tree is integration-tested end-to-end, and the README documents the CLI for new users
**Depends on**: Phase 11
**Requirements**: UTIL-02, UTIL-03
**Success Criteria** (what must be TRUE):
  1. `bunnycdn stats [--pull-zone-id <id>] [--from <date>] [--to <date>]` displays CDN statistics via Rich table or `--json`
  2. `bunnycdn billing` displays account billing summary via Rich table or `--json`
  3. The README contains a CLI section with install instructions, all command groups, env var reference, and a `--json | jq` example
**Plans**: TBD

## Progress

**Execution Order:** Phases execute in numeric order: 08 → 09 → 10 → 11 → 12

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 01. Package Scaffold & Exception Hierarchy | v1.0 | 2/2 | Complete | 2026-04-10 |
| 02. Base Client Infrastructure | v1.0 | 2/2 | Complete | 2026-04-10 |
| 03. Core & Storage API Clients | v1.0 | 2/2 | Complete | 2026-04-10 |
| 04. Test Suite | v1.0 | 2/2 | Complete | 2026-04-10 |
| 05. Quality & Coverage | v1.1 | 2/2 | Complete | 2026-04-10 |
| 06. RetryTransport | v1.1 | 2/2 | Complete | 2026-04-10 |
| 07. Constructor Integration | v1.1 | 2/2 | Complete | 2026-04-10 |
| 08. CLI Scaffold | v2.0 | 2/2 | Complete   | 2026-04-11 |
| 09. Output Layer & Error Handling | v2.0 | 0/1 | Not started | - |
| 10. CoreClient Sub-Apps | v2.0 | 0/? | Not started | - |
| 11. StorageClient Sub-App | v2.0 | 0/? | Not started | - |
| 12. Utility Commands & Integration | v2.0 | 0/? | Not started | - |

---

*See [MILESTONES.md](MILESTONES.md) for shipped milestone details.*
