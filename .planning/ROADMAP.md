# Roadmap: bunny-cdn-sdk

## Milestones

- ✅ **[v1.0 MVP](milestones/v1.0-ROADMAP.md)** *(shipped 2026-04-10)* — CoreClient (37 methods), StorageClient (4 ops, 10 regions), httpx infrastructure, 58-test suite (96% coverage)
- ✅ **[v1.1 Reliability & Coverage](milestones/v1.1-ROADMAP.md)** *(shipped 2026-04-10)* — RetryTransport, constructor retry kwargs, coverage gaps closed, 98 tests (99% coverage)
- ✅ **[v2.0 Typer CLI](milestones/v2.0-ROADMAP.md)** *(shipped 2026-04-11)* — Optional [cli] extra with 5 sub-command groups, 47 requirements, 241 tests
- 🚧 **v2.1 Release Engineering** — Phases 13–16 (in progress)

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

### 🚧 v2.1 Release Engineering (In Progress)

**Milestone Goal:** Ship a production-ready release pipeline — version hygiene, build verification, tox quality gates, GHA CI, Dependabot, and Trusted Publishing to TestPyPI and production PyPI.

- [x] **Phase 13: Version & Metadata** - pyproject.toml as single source of truth; `bunnycdn.__version__` via importlib.metadata; complete package metadata; CHANGELOG.md; build artifacts verified (completed 2026-04-11)
- [x] **Phase 14: tox & Local Quality Gates** - tox-uv config covering py312/py313/py314 test envs plus lint and typecheck envs; all envs pass locally (completed 2026-04-11)
- [ ] **Phase 15: CI & Dependabot** - GHA CI workflow running all tox envs on push/PR with uv caching; Dependabot monitoring pip and GitHub Actions ecosystems
- [ ] **Phase 16: Publishing Pipeline** - Trusted Publishing (OIDC) configured on PyPI and TestPyPI; release workflow auto-publishes on v* tags; TestPyPI smoke test verified

## Phase Details

### Phase 13: Version & Metadata
**Goal**: Package metadata is complete, version is a single source of truth in pyproject.toml, `bunnycdn.__version__` works at runtime, CHANGELOG.md exists, and build artifacts pass PyPI validation
**Depends on**: Phase 12 (v2.0 ships first)
**Requirements**: VERSION-01, VERSION-02, VERSION-03, BUILD-01, BUILD-02, BUILD-03
**Success Criteria** (what must be TRUE):
  1. `import bunnycdn; bunnycdn.__version__` returns the current version string at runtime without hardcoding it
  2. Version appears only in `pyproject.toml` — no duplicate definition in `__init__.py` or any other file
  3. `CHANGELOG.md` exists and documents v1.0, v1.1, v2.0, and v2.1 entries
  4. `uv build` completes without errors and produces a `.whl` and `.tar.gz` in `dist/`
  5. `twine check dist/*` reports no errors or warnings for either artifact
**Plans**: 3 plans

Plans:
- [x] 13-01-PLAN.md — `__version__` via importlib.metadata + complete pyproject.toml metadata
- [x] 13-02-PLAN.md — CHANGELOG.md with v1.0–v2.1 entries
- [x] 13-03-PLAN.md — Build verification: `uv build` + `twine check dist/*`

### Phase 14: tox & Local Quality Gates
**Goal**: Developers can run `uv run tox` locally and get isolated test runs across Python 3.12/3.13/3.14, plus dedicated lint and typecheck environments, all passing
**Depends on**: Phase 13
**Requirements**: TOX-01, TOX-02, TOX-03, TOX-04
**Success Criteria** (what must be TRUE):
  1. `tox.ini` (or `pyproject.toml` tox config) defines `py312`, `py313`, and `py314` envs that each run the full pytest suite
  2. tox-uv plugin is used so env creation is fast and pip is not invoked
  3. Separate `lint` and `typecheck` tox envs exist and run ruff and ty respectively
  4. `uv run tox` completes with all envs passing (exit 0)
**Plans**: 2 plans

Plans:
- [x] 14-01-PLAN.md — Write tox.ini (uv-venv-lock-runner, 5 envs) + ruff per-file-ignores + auto-fix
- [x] 14-02-PLAN.md — Fix residual ruff errors manually + end-to-end `uv run tox` gate

### Phase 15: CI & Dependabot
**Goal**: Every push and pull request automatically runs all tox envs on GitHub Actions with caching; Dependabot opens PRs for outdated pip and GitHub Actions dependencies
**Depends on**: Phase 14
**Requirements**: CI-01, CI-02, CI-03, CI-04, DEPS-01, DEPS-02
**Success Criteria** (what must be TRUE):
  1. `.github/workflows/ci.yml` triggers on both `push` and `pull_request` events
  2. CI runs lint, typecheck, py312, py313, and py314 tox envs and fails the check if any env fails
  3. CI builds the wheel and sdist and runs `twine check` on them as part of the workflow
  4. uv and tox environments are cached so subsequent CI runs are noticeably faster than cold runs
  5. `.github/dependabot.yml` monitors pip and GitHub Actions ecosystems weekly and opens automated PRs
**Plans**: TBD

### Phase 16: Publishing Pipeline
**Goal**: The project can publish to TestPyPI and production PyPI via OIDC Trusted Publishing, triggered automatically by a v* tag push or manually via workflow_dispatch; TestPyPI install verified
**Depends on**: Phase 15
**Requirements**: PUBLISH-01, PUBLISH-02, PUBLISH-03, PUBLISH-04, PUBLISH-05, PUBLISH-06
**Success Criteria** (what must be TRUE):
  1. PyPI and TestPyPI Trusted Publishing (OIDC) are configured — no API tokens stored in GitHub secrets
  2. `.github/workflows/release.yml` triggers automatically on a `v*` tag push and publishes the package
  3. The release workflow includes `workflow_dispatch` so a maintainer can manually trigger a publish without pushing a tag
  4. A publish to TestPyPI succeeds and `pip install --index-url https://test.pypi.org/simple/ bunny-cdn-sdk` followed by `import bunnycdn` works
  5. The production PyPI publish workflow is wired and ready but not yet triggered
**Plans**: TBD

## Progress

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
| 13. Version & Metadata | v2.1 | 3/3 | Complete   | 2026-04-11 |
| 14. tox & Local Quality Gates | v2.1 | 2/2 | Complete   | 2026-04-11 |
| 15. CI & Dependabot | v2.1 | 0/? | Not started | - |
| 16. Publishing Pipeline | v2.1 | 0/? | Not started | - |

---

*See [MILESTONES.md](MILESTONES.md) for shipped milestone details.*
