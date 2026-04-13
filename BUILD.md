# Build & Development Guide

This project uses `uv` as the package manager and `poethepoet` for task automation. All build scripts can be run locally or in CI/CD environments.

## Quick Start

```bash
# Install dependencies
uv run poe install

# Run all checks (lint + test)
uv run poe ci-all
```

## Available Tasks

### Setup

```bash
uv run poe install      # Install all dependencies (dev, lint, test, audit)
uv run poe dev          # Alias for install
```

### Code Quality

```bash
uv run poe fix          # Auto-fix issues and format code (ruff check --fix && ruff format)
uv run poe format       # Auto-format code with ruff (format only)
uv run poe lint         # Check formatting, linting, and type checking
uv run poe check        # Alias for lint
uv run poe type         # Run type checker (ty)
```

### Testing

```bash
uv run poe test         # Run tests with coverage (80% threshold)
uv run poe test-verbose # Run tests with verbose output
uv run poe test-cov     # Generate HTML coverage report in htmlcov/
```

### Security & Pre-commit Hooks

```bash
uv run poe audit        # Run prek pre-commit hooks (ruff check --fix, ruff format)
uv run poe security     # Alias for audit
```

See `prek.toml` for hook configuration.

### Building & Distribution

```bash
uv run poe build        # Build wheel and sdist packages
uv run poe clean        # Remove build artifacts and cache files
uv run poe dist         # Clean and rebuild packages
```

### CI/CD

```bash
uv run poe ci-all       # Run all CI checks (lint + test)
uv run poe ci-lint      # Run only linting checks
uv run poe ci-test      # Run only tests
```

## Listing All Tasks

```bash
# List all available poe tasks
uv run poe
```

## GitHub Actions Workflows

The repository includes automated workflows:

- **`test.yml`** — Runs tests on all PRs and pushes to main (matrix: Python 3.12, 3.13)
- **`security.yml`** — Runs security audit weekly + on PRs
- **`dependabot-auto-merge.yml`** — Auto-merges dev dependency updates
- **`dependabot-lock-file.yml`** — Keeps `uv.lock` in sync with Dependabot PRs

## Development Workflow

### Before Committing

```bash
# Auto-fix issues and format code
uv run poe fix

# Run all checks
uv run poe lint

# Run tests with coverage
uv run poe test-cov
```

### Before Pushing

```bash
# Run everything (like CI does)
uv run poe ci-all

# Check security
uv run poe audit
```

### Building for Release

```bash
# Build packages
uv run poe build

# Outputs to dist/:
#  - bunny-cdn-sdk-X.Y.Z-py3-none-any.whl
#  - bunny-cdn-sdk-X.Y.Z.tar.gz
```

## Coverage Reports

After running `uv run poe test-cov`, open the HTML report:

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Troubleshooting

### "command not found: uv"
Install uv: https://github.com/astral-sh/uv

### "command not found: poe"
Make sure dependencies are installed: `uv sync --all-groups`

### "command not found: prek"
Install prek: https://prek.j178.dev/installation/

Or use the pre-built binary from GitHub releases: https://github.com/j178/prek/releases

### Lock file conflicts
If `uv.lock` is out of sync:
```bash
uv lock --upgrade
```

### Python version mismatch
Ensure Python 3.12+ is available:
```bash
python3 --version
```
