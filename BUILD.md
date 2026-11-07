# Build & Development Guide

This project uses **layered tooling** with clear responsibilities:

- **`uv`** — Package manager and virtual environments
- **`poe`** (poethepoet) — Python task orchestration
- **`prek`** — Pre-commit hooks (file validation, formatting, security)
- **GitHub Actions** — Thin CI/CD layer that calls `poe`

## Quick Start

```bash
uv run poe install-deps   # Install all dev dependencies and optional extras (incl. CLI)
uv run poe test-all       # Run all CI checks: lint + type + pytest
```

## Architecture

```
GitHub Actions  →  uv run poe test-all  →  ┬─→ test-lint   (ruff check --fix, ruff format, prek)
                                            ├─→ test-type   (ty)
                                            └─→ test-pytest (pytest, 80% coverage gate)
```

## Available poe Tasks

Run `uv run poe` to list them all.

### Setup
```bash
uv run poe install-deps   # uv sync --all-groups --all-extras
```

### Checks
```bash
uv run poe test-lint      # ruff check --fix + ruff format on src/ tests/, then prek on all files
uv run poe test-type      # ty check src/
uv run poe test-pytest    # pytest in parallel, fails under 80% coverage
uv run poe test-cov       # pytest + HTML coverage report in htmlcov/
uv run poe test-all       # test-lint → test-type → test-pytest (what CI runs)
```

### Build
```bash
uv run poe build          # Clean build/, dist/ and build wheel + sdist into dist/
```

### Version
```bash
uv run poe version        # Show current version
uv run poe version-patch  # X.Y.Z → X.Y.Z+1
uv run poe version-minor  # X.Y.Z → X.Y+1.0
uv run poe version-major  # X.Y.Z → X+1.0.0
```

### Release
```bash
uv run poe version-minor  # (or patch/major) — required first
uv run poe release
```

`release` runs `test-all`, commits the version bump, tags `vX.Y.Z`, builds, pushes the branch **and the tag**, and opens a PR to `main`.
Pushing a `v*` tag triggers `publish.yml`, which publishes to PyPI immediately — before the PR is reviewed or merged.
To publish only after merge, bump and commit normally, then tag `main` after merging:

```bash
git tag vX.Y.Z && git push origin vX.Y.Z
```

## Pre-commit Hooks (prek)

Configuration is in `prek.toml`.

**Code Quality (ruff):** `ruff --fix`, `ruff-format`

**File Validation:** `check-json`, `check-toml`, `check-yaml`, `check-xml`, `check-vcs-permalinks`, `check-symlinks`, `destroyed-symlinks`, `mixed-line-ending` (LF)

**Security / Safety:** `detect-private-key`, `check-merge-conflict`, `no-commit-to-branch` (blocks direct commits to `main`)

**GitHub config:** `check-dependabot`, `check-github-workflows`

```bash
uv run prek run                # Staged files only (what git hooks run)
uv run prek run --all-files    # All files (what test-lint runs)
uv run prek list               # List configured hooks
uv run prek install            # Install the git pre-commit hook
```

`prek` is a dev dependency, so `uv run prek` works without a separate install.

## GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR to `main` | `uv run poe install-deps` + `uv run poe test-all` (matrix: Python 3.12–3.15) |
| `publish.yml` | Push of a `v*` tag | Build and publish to PyPI via OIDC trusted publishing |
| `dependabot-auto-merge.yml` | Dependabot PRs | Auto-merge dev dependency updates (`chore(deps-dev)`); production deps need manual review |

## Coverage Reports

```bash
uv run poe test-cov
open htmlcov/index.html  # macOS
```

## Troubleshooting

### "command not found: uv"
Install: https://github.com/astral-sh/uv

### `ty` reports `Cannot resolve imported module typer`
The CLI extra isn't installed. Run `uv run poe install-deps`.

### Lock file conflicts
```bash
uv lock --upgrade
```
