# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-04-11

### Added
- `bunnycdn.__version__` attribute via `importlib.metadata` — single source of truth in `pyproject.toml`
- `CHANGELOG.md` (this file)
- Complete PyPI package metadata: license, classifiers, project URLs, keywords, readme linkage
- Build verification: `uv build` + `twine check` gate added to development workflow

## [2.0.0] - 2026-04-11

### Added
- Optional `[cli]` extra (`pip install bunny-cdn-sdk[cli]`) with Typer + Rich
- `bunnycdn` entry point with five sub-command groups:
  - `bunnycdn pull-zone` — list, get, create, update, delete, purge
  - `bunnycdn storage-zone` — list, get, create, update, delete
  - `bunnycdn dns-zone` — list, get, create, update, delete; nested `dns-zone record` commands
  - `bunnycdn video-library` — list, get, create, update, delete
  - `bunnycdn storage` — list, upload, download, delete (uses StorageClient with separate auth)
- `bunnycdn stats` and `bunnycdn billing` utility commands
- `--json` flag on all commands for machine-readable output
- Rich table rendering for human-readable output
- `ImportError` guard in CLI module to provide clear message when `[cli]` extra is missing
- 241 tests total (110+ CliRunner tests for CLI layer)

### Notes
- CLI dependencies (`typer`, `rich`) in `[project.optional-dependencies]` not `[dependency-groups]`
- Entry point name is `bunnycdn` (not `bunny`) to avoid PyPI collision with `bunny` file-watcher package
- Local imports inside command functions prevent circular imports

## [1.1.0] - 2026-04-10

### Added
- `RetryTransport` — composable `httpx.BaseTransport` subclass with exponential backoff and jitter
- `max_retries` and `backoff_base` constructor kwargs on both `CoreClient` and `StorageClient`
- 15 integration tests for retry behavior
- 98 tests total, 99% coverage

### Changed
- `RetryTransport` is composable — can wrap any `httpx.BaseTransport`, not tied to client constructors

## [1.0.0] - 2026-04-10

### Added
- `CoreClient` covering Pull Zones, Storage Zones (management), DNS Zones, Video Libraries,
  Statistics, Billing, Purge, API Keys, Countries, and Regions — 37 methods total
- `StorageClient` with list, upload, download, delete operations across 10 storage regions
- Sync public API backed by async `httpx` internals for concurrent batch operations
- `iter_*` methods on `CoreClient` for auto-paginated iteration
- Batch fetch support (`get_pull_zones([id1, id2, id3])`) via concurrent async requests
- Full exception hierarchy: `BunnySDKError`, `BunnyAPIError`, `BunnyAuthenticationError`,
  `BunnyNotFoundError`, `BunnyRateLimitError`, `BunnyServerError`, `BunnyConnectionError`,
  `BunnyTimeoutError`
- `AccessKey` header injection per-client (no credential sharing between clients)
- `py.typed` marker for PEP 561 typed package support
- 58 tests, 96% coverage

[Unreleased]: https://github.com/yolabingo/bunny-cdn-python-sdk/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/yolabingo/bunny-cdn-python-sdk/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/yolabingo/bunny-cdn-python-sdk/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/yolabingo/bunny-cdn-python-sdk/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/yolabingo/bunny-cdn-python-sdk/releases/tag/v1.0.0
