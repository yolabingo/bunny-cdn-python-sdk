# Build & Development Guide

This project uses **layered tooling** with clear responsibilities:

- **`uv`** — Package manager and virtual environments
- **`poe`** (poethepoet) — Python task orchestration
- **`prek`** — Pre-commit hooks (file validation, formatting, security)
- **GitHub Actions** — Thin CI/CD layer that calls `poe`

## Quick Start

```bash
# Install dependencies
uv run poe install

# Run all CI checks (lint via prek, type check, tests)
uv run poe ci
```

## Architecture

```
GitHub Actions  →  uv run poe ci  →  ┬─→ prek (lint/format/validate)
                                      ├─→ ty (type check)
                                      └─→ pytest (tests)
```

Each tool plays to its strengths — no duplication.

## Available poe Tasks

### Setup
```bash
uv run poe install      # Install all dev dependencies
```

### Quality Checks
```bash
uv run poe lint         # Run prek hooks (ruff, JSON/YAML/TOML/secret checks)
uv run poe fix          # Same as lint — prek auto-fixes
uv run poe type         # Type check with ty
```

### Testing
```bash
uv run poe test         # Run tests with 80% coverage threshold
uv run poe test-cov     # Generate HTML coverage report in htmlcov/
```

### Build & Distribution
```bash
uv run poe build        # Build wheel + sdist
uv run poe clean        # Remove build artifacts
uv run poe dist         # clean + build
```

### CI Bundle
```bash
uv run poe ci           # lint + type + test (the canonical CI command)
```

### List All Tasks
```bash
uv run poe              # Lists all available tasks
```

## Pre-commit Hooks (prek)

Configuration is in `prek.toml`. Hooks are organized by concern:

**Code Quality (ruff):**
- `ruff check --fix` — Auto-fix linting issues
- `ruff-format` — Format Python code

**File Validation:**
- `check-json`, `check-toml`, `check-yaml`, `check-xml`
- `check-vcs-permalinks`

**File Integrity:**
- `mixed-line-ending` — Normalize to LF
- `check-symlinks`, `destroyed-symlinks`

**Security:**
- `detect-private-key`
- `check-merge-conflict`
- `no-commit-to-branch` (blocks direct commits to main)

### Install prek locally

```bash
brew install j178/tap/prek                            # macOS/Linux
# or download: https://github.com/j178/prek/releases
```

### Run prek directly

```bash
prek run                # Staged files only (what git hooks run)
prek run --all-files    # All files in repo (what CI runs)
prek list               # List configured hooks
```

## GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR to main | Run `uv run poe ci` (matrix: Python 3.12, 3.13) |
| `dependabot-auto-merge.yml` | Dependabot PRs | Auto-merge dev dependency updates |
| `dependabot-lock-file.yml` | Dependabot PRs | Keep `uv.lock` in sync |

## Development Workflow

### Before Committing
```bash
uv run poe fix          # Auto-fix lint/format via prek
uv run poe type         # Type check
uv run poe test         # Run tests
```

### Before Pushing (or just trust CI)
```bash
uv run poe ci           # Same checks as CI
```

### Building for Release
```bash
uv run poe dist         # Clean + build → dist/*.whl, dist/*.tar.gz
```

## Coverage Reports

```bash
uv run poe test-cov
open htmlcov/index.html  # macOS
```

## Troubleshooting

### "command not found: uv"
Install: https://github.com/astral-sh/uv

### "command not found: poe"
Run `uv sync --all-groups`

### "command not found: prek"
Install: `brew install j178/tap/prek` or https://github.com/j178/prek/releases

### Lock file conflicts
```bash
uv lock --upgrade
```
