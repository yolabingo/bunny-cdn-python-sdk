# Technology Stack: v2.0 Typer CLI Addition

**Project:** bunny-cdn-sdk
**Milestone:** v2.0 — Optional Typer CLI
**Researched:** 2026-04-10
**Scope:** Additions only — existing httpx/uv/Python 3.12+ stack is validated and unchanged

---

## New Dependencies

### Runtime — Optional `[cli]` Extra

| Library | Pin | Confidence | Why This Version |
|---------|-----|------------|-----------------|
| `typer` | `>=0.12.0` | MEDIUM | 0.12 was the breaking refactor that made Rich optional; `[all]` extra no longer needed — Rich is a peer dep, not bundled. Pinning `>=0.12` excludes the old bundled-Rich API while staying open to patch/minor updates. |
| `rich` | `>=13.0.0` | HIGH | Rich 14.3.3 already present in uv.lock (pulled in by pip-audit). Confirmed Python 3.12+ and 3.14 compatible. Setting floor at 13.0 ensures `Table`, `Console`, and `Pretty` APIs used by v2.0 CLI are available. Rich does not break public API within major version. |

**Confidence note on Typer version:** Training knowledge goes through ~0.12-0.15 series (Aug 2025 cutoff). WebSearch and WebFetch were unavailable for live verification. Recommend running `uv add typer` without a pin first to confirm latest stable during implementation, then backfill the exact version into pyproject.toml. The `>=0.12.0` floor is the safe minimum.

**Click:** Typer uses Click internally but Click is a transitive dep — do NOT pin Click directly in pyproject.toml. Typer manages its own Click constraint. Adding a direct Click pin creates version-conflict risk and no benefit.

---

## pyproject.toml Configuration

### Optional Dependencies (`[cli]` extra)

```toml
[project.optional-dependencies]
cli = [
    "typer>=0.12.0",
    "rich>=13.0.0",
]
```

**Why `[project.optional-dependencies]` not `[dependency-groups]`:**
- `[dependency-groups]` (PEP 735) is for local dev tooling — it does NOT get published to PyPI and cannot be `pip install`-ed by end users.
- `[project.optional-dependencies]` is the PEP 508 mechanism for publishable extras — `pip install bunny-cdn-sdk[cli]` works only from this table.
- The existing project already uses `[dependency-groups]` correctly for dev-only tooling (lint, test, audit) — this pattern holds, CLI is user-facing so it goes in `[project.optional-dependencies]`.

### Entry Point

```toml
[project.scripts]
bunny = "bunny_cdn_sdk.cli:app"
```

**`[project.scripts]` vs `[project.entry-points]`:**
- `[project.scripts]` is the standard mechanism for console_scripts. It is equivalent to `[project.entry-points."console_scripts"]` — use the short form.
- The value `bunny_cdn_sdk.cli:app` means: import `app` from `src/bunny_cdn_sdk/cli.py`. The `app` should be a `typer.Typer()` instance (not a function), matching Typer's standard pattern.
- The entry point is active whenever the package is installed (even without `[cli]`). Guard against missing optional deps with a lazy import inside `cli.py` that raises a clear `ImportError` if Typer is not installed.

### uv sync for dev with CLI deps

```bash
uv sync --all-groups --extra cli
```

This pulls in `typer` and `rich` alongside existing dev tooling. Add this as a poe task variant if needed:

```toml
[tool.poe.tasks]
dev-cli = "uv sync --all-groups --extra cli"
```

---

## Async-in-CLI: The `asyncio.run()` Bridge

The existing SDK has a sync public API (methods like `core.list_pull_zones()` call `asyncio.run()` internally via `_run()`). Typer commands are synchronous.

**How it works:** Typer commands call the SDK's existing sync methods directly — no `asyncio.run()` needed in CLI code. The async execution happens inside the SDK, invisible to the CLI layer.

```python
# cli.py — what NOT to do
@app.command()
async def list_pull_zones(...):          # wrong — Typer doesn't support async commands natively
    zones = await core.list_pull_zones()

# cli.py — what to do
@app.command()
def list_pull_zones(...):                # correct — sync call, async happens inside SDK
    zones = core_client.list_pull_zones()
```

**If any v2.0 feature needs to call async code directly** (e.g., a CLI operation that is not yet exposed via sync SDK methods): use `anyio.from_thread.run_sync()` or simply `asyncio.run()` at the top of the command. `anyio` is already in the lock (pulled by httpx). Prefer `asyncio.run()` — it's stdlib and zero extra imports.

```python
import asyncio

@app.command()
def some_command():
    result = asyncio.run(_some_async_helper())
```

Do not use `anyio.run()` as the CLI bridge — it adds unnecessary framework coupling for what is essentially a one-liner.

---

## Rich Usage Pattern

Rich is a peer dep, not bundled by Typer in 0.12+. Import directly:

```python
from rich.console import Console
from rich.table import Table

console = Console()
```

**Do NOT** use `typer.echo()` for Rich output — it bypasses Rich's styling. Use `console.print()`.

**`--json` flag pattern:**

```python
import json
from rich.console import Console
from rich.table import Table

console = Console()

@app.command()
def list_pull_zones(
    api_key: str = typer.Option(..., envvar="BUNNY_API_KEY"),
    json_output: bool = typer.Option(False, "--json"),
):
    client = CoreClient(api_key=api_key)
    zones = client.list_pull_zones()
    if json_output:
        typer.echo(json.dumps(zones, indent=2))
    else:
        table = Table(...)
        console.print(table)
```

---

## Lazy Import Guard (Entry Point Safety)

The `[project.scripts]` entry point is always installed. If a user installs `bunny-cdn-sdk` without `[cli]`, running `bunny` must fail gracefully:

```python
# src/bunny_cdn_sdk/cli.py — top of file
try:
    import typer
    from rich.console import Console
except ImportError as e:
    raise ImportError(
        "The 'cli' extra is required: pip install bunny-cdn-sdk[cli]"
    ) from e
```

---

## File Layout

```
src/bunny_cdn_sdk/
    cli.py          # new — Typer app, subcommand groups
    cli/            # alternative if commands grow large — optional split
        __init__.py
        pull_zone.py
        storage_zone.py
        ...
```

Start with `cli.py` (single file). Split into `cli/` package only if it exceeds ~300 lines.

---

## What Does NOT Change

| Component | Status |
|-----------|--------|
| `httpx>=0.28.1` | Unchanged — CLI calls SDK sync methods |
| Python `>=3.12` | Unchanged |
| `uv_build` backend | Unchanged |
| `[dependency-groups].dev` | Unchanged — add `dev-cli` task if needed |
| `RetryTransport` | Unchanged — CLI users get retry via constructor kwargs |
| Plain `dict` returns | Unchanged — CLI formats dicts into Rich tables |
| `ty` type checker | Unchanged — CLI code must pass `ty check src/` |

---

## Sources

| Claim | Source | Confidence |
|-------|--------|------------|
| Rich 14.3.3 version | uv.lock (verified in repo, upload-time 2026-02-19) | HIGH |
| Rich Python 3.12/3.14 support | `.venv/lib/python3.14/site-packages/rich-14.3.3.dist-info/METADATA` (installed, confirmed) | HIGH |
| Typer 0.12 broke out Rich as peer dep | Training knowledge (Aug 2025 cutoff) | MEDIUM |
| `[project.optional-dependencies]` vs `[dependency-groups]` | PEP 508 / PEP 735 spec — training knowledge | HIGH |
| `[project.scripts]` entry point syntax | uv documentation, PEP 517 — training knowledge | HIGH |
| asyncio.run() for CLI→async bridge | Training knowledge, consistent with httpx docs | HIGH |
| Click is transitive via Typer | Training knowledge | MEDIUM |
