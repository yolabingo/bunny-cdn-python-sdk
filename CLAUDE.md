## Project

**bunny-cdn-sdk**

A thin, typed Python SDK wrapping the Bunny CDN REST APIs using `httpx2`. Provides four service clients — Core, Storage, Shield, Logging — with a sync public API and thread-pooled concurrent batch operations. Designed for Python developers who need a clean, dependency-light interface to Bunny CDN without any magic.

**Core Value:** A Python developer can `pip install bunny-cdn-sdk`, instantiate a client with their API key, and call methods that map 1:1 to Bunny CDN endpoints — no surprises, no hidden behavior.

### Constraints

- **Tech stack**: httpx2 only — no httpx, requests, aiohttp, or other HTTP libs (applies to the SDK in `src/`; maintainer scripts in `tools/` use only the stdlib)
- **Python version**: 3.12+
- **Package manager**: `uv` — not pip directly; always run commands as `uv run <cmd>` (never invoke python, pytest, ruff, ty directly)
- **Dependencies**: change `pyproject.toml` deps only with `uv add` / `uv remove` (`--group <name>`, `--dev`, `--optional <extra>`), never by hand, with a `>=` lower bound (pass `'pkg>=X.Y'` explicitly when re-adding an existing dep — `uv add` won't add one to an unbounded entry); the one exception is deleting an emptied group and its `include-group` line, which uv can't do
- **Type checker**: `ty` — not mypy or pyright
- **Return types**: plain `dict` from `response.json()` — no Pydantic, no dataclasses
- **Auth**: `AccessKey` header injection per-client — no credential sharing between clients
- **API fidelity**: method signatures match the design doc ([docs/DESIGN.md](docs/DESIGN.md)) exactly — no deviation without explicit decision

### Dev workflow

- **Tasks**: run everything through poe (`uv run poe <task>`; `uv run poe` lists them). Task list and details are in [docs/BUILD.md](docs/BUILD.md). Use the `poe-tasks` skill (`.claude/skills/poe-tasks/`) before adding or changing a task.
- **Before finishing a change**: run `uv run poe test-all` (lint + prek hooks + ty + pytest at ≥80% coverage). This is what CI runs.
- **Dependency audit**: `uv run poe test-audit` (`uv audit`, which is experimental in uv) runs locally and as a prek hook when `uv.lock` or `pyproject.toml` change. CI skips the hook and runs the audit as a non-blocking step, so a newly published vulnerability never fails CI.
- **Release**: `poe release` tags and pushes, and the tag publishes to PyPI. Don't run it unless asked.

### Bunny API specs ([docs/apis/](docs/apis/))

Bunny's published OpenAPI/Swagger specs, saved as gzipped JSON snapshots: `core.json.gz` (api.bunny.net: pull/storage/DNS zones, billing, …), `shield.json.gz`, `logging.json.gz`, `storage.json.gz` (Edge Storage), `stream.json.gz`, `edge-scripting.json.gz`, `magic-containers.json.gz`, `origin-errors.json.gz`. `manifest.json` stays uncompressed.

- **Source of truth**: use these specs when adding or checking an endpoint (paths, methods, params, request/response schemas). Prefer them over memory or web search; then record the method in `docs/DESIGN.md`, as the API-fidelity rule requires.
- **Generated files**: don't edit them by hand; `tools/fetch_api_specs.py` writes them.
  - `uv run poe api-specs` refreshes the specs and prints which were added, changed or removed.
  - `uv run poe api-specs-check` makes no changes and exits 1 if Bunny's published specs differ from the saved ones.
- **Manifest**: `docs/apis/manifest.json` records each spec's source URL, `info.version`, path count, SHA-256 and `updated_at`. Bunny rarely bumps `info.version`, so detect changes by hash and review them with `git diff docs/apis/`. Readable diffs need `git config diff.gzip.textconv "gzip -dc"` once per clone, which `.gitattributes` relies on.
- **Reading them**: specs can't be read directly (`core.json` is about 500 KB uncompressed). Query them with a script, for example `uv run python -c "import gzip, json; s = json.load(gzip.open('docs/apis/core.json.gz')); print([p for p in s['paths'] if 'dnszone' in p])"`, or `gzip -dc docs/apis/core.json.gz | jq '.paths | keys'`.
