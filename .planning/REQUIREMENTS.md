# Requirements: bunny-cdn-sdk v2.1 Release Engineering

**Milestone:** v2.1 Release Engineering
**Status:** Active
**Created:** 2026-04-11

## v2.1 Requirements

### Version Management

- [ ] **VERSION-01**: `bunnycdn.__version__` returns the current package version at runtime (via `importlib.metadata`)
- [ ] **VERSION-02**: Version is defined only in `pyproject.toml` — no duplication in `__init__.py` or elsewhere
- [ ] **VERSION-03**: `CHANGELOG.md` exists with entries covering v1.0 through v2.1

### Build Verification

- [ ] **BUILD-01**: `uv build` produces a wheel and sdist without errors
- [ ] **BUILD-02**: `twine check dist/*` passes for both artifacts (valid PyPI metadata)
- [ ] **BUILD-03**: `pyproject.toml` metadata is complete — name, version, description, author, license, classifiers, project URLs

### tox

- [ ] **TOX-01**: tox configured with `py312`, `py313`, and `py314` envs that each run the full pytest suite
- [ ] **TOX-02**: tox-uv plugin used (fast venv creation, no pip overhead)
- [ ] **TOX-03**: Separate tox envs for `lint` (ruff) and `typecheck` (ty)
- [ ] **TOX-04**: `uv run tox` passes all envs locally

### CI (GitHub Actions)

- [ ] **CI-01**: `.github/workflows/ci.yml` triggers on push and pull_request
- [ ] **CI-02**: CI runs tox lint, typecheck, and test envs (py312, py313, py314)
- [ ] **CI-03**: CI produces and validates the wheel/sdist build artifact
- [ ] **CI-04**: uv + tox environments are cached for faster subsequent runs

### Dependabot

- [ ] **DEPS-01**: `.github/dependabot.yml` monitors pip ecosystem dependencies weekly
- [ ] **DEPS-02**: `.github/dependabot.yml` monitors GitHub Actions dependencies weekly

### Publishing

- [ ] **PUBLISH-01**: PyPI Trusted Publishing (OIDC) configured — no stored tokens
- [ ] **PUBLISH-02**: TestPyPI Trusted Publishing configured for pre-release validation
- [ ] **PUBLISH-03**: `.github/workflows/release.yml` auto-publishes on `v*` tag push
- [ ] **PUBLISH-04**: Release workflow includes `workflow_dispatch` for manual trigger
- [ ] **PUBLISH-05**: TestPyPI publish verified — install + import succeeds
- [ ] **PUBLISH-06**: Production PyPI workflow ready but not yet triggered

## Future Requirements

*(None identified — scope is intentionally narrow for this milestone)*

## Out of Scope

| Feature | Reason |
|---------|--------|
| Python 3.10/3.11 support | Requires avoiding 3.12-only syntax; not worth the constraint |
| Automated version bumping (hatch-vcs, setuptools-scm) | Manual pyproject.toml bump is sufficient; no tag-driven versioning needed |
| Release notes auto-generation | CHANGELOG.md maintained manually |
| `--output yaml` in CLI | Adds PyYAML dep; JSON + jq is the standard |
| conda/mamba packaging | pip/PyPI is the target distribution channel |

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| VERSION-01 | Phase 13 | Pending |
| VERSION-02 | Phase 13 | Pending |
| VERSION-03 | Phase 13 | Pending |
| BUILD-01 | Phase 13 | Pending |
| BUILD-02 | Phase 13 | Pending |
| BUILD-03 | Phase 13 | Pending |
| TOX-01 | Phase 14 | Pending |
| TOX-02 | Phase 14 | Pending |
| TOX-03 | Phase 14 | Pending |
| TOX-04 | Phase 14 | Pending |
| CI-01 | Phase 15 | Pending |
| CI-02 | Phase 15 | Pending |
| CI-03 | Phase 15 | Pending |
| CI-04 | Phase 15 | Pending |
| DEPS-01 | Phase 15 | Pending |
| DEPS-02 | Phase 15 | Pending |
| PUBLISH-01 | Phase 16 | Pending |
| PUBLISH-02 | Phase 16 | Pending |
| PUBLISH-03 | Phase 16 | Pending |
| PUBLISH-04 | Phase 16 | Pending |
| PUBLISH-05 | Phase 16 | Pending |
| PUBLISH-06 | Phase 16 | Pending |
