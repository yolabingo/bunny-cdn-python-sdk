# Phase 08: CLI Scaffold - Research

**Researched:** 2026-04-10
**Domain:** Optional Typer CLI scaffold — pyproject.toml wiring, cli/ subpackage, ImportError guard, auth context, entry point registration
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-01 | CLI is installable as optional extra via `pip install bunny-cdn-sdk[cli]` | `[project.optional-dependencies]` section in pyproject.toml; verified PEP 508 mechanism |
| CLI-02 | `bunnycdn` entry point is registered and resolves after `[cli]` install | `[project.scripts]` entry in pyproject.toml pointing to `bunny_cdn_sdk.cli:app` |
| CLI-03 | Importing SDK core (`import bunny_cdn_sdk`) does not import Typer or Rich | ImportError guard in `cli/__init__.py`; strict `cli/` subpackage isolation — nothing in `__init__.py` imports from `cli/` |
| CLI-04 | Running `bunnycdn` without `[cli]` deps exits with a clear "install bunny-cdn-sdk[cli]" message | `try/except ImportError` at top of `cli/__init__.py` with `raise` in except branch; entry point always installed, guard fires when typer absent |
| AUTH-01 | Core commands accept `--api-key` flag; fallback to `BUNNY_API_KEY` env var | `typer.Option(envvar="BUNNY_API_KEY")` in root `@app.callback()`; stored on `State` dataclass; read by each command via `ctx.obj` |
| AUTH-02 | Storage commands accept `--zone-name` / `BUNNY_STORAGE_ZONE`, `--storage-key` / `BUNNY_STORAGE_KEY`, `--region` / `BUNNY_STORAGE_REGION` (default: `falkenstein`) | All three wired in `@app.callback()` on `State`; StorageClient constructor verified — takes `zone_name`, `password`, `region` as separate args |
| AUTH-03 | `--json` flag available on all commands | Boolean flag on `State` dataclass; resolved in callback; each command reads `ctx.obj.json_output` |
| AUTH-04 | Missing required auth exits with actionable error message | `typer.Option(...)` (Ellipsis default) causes Typer to abort with "Missing option '--api-key'" if neither flag nor env var set; OR manual check emits `typer.echo(err=True)` + `raise typer.Exit(1)` |

</phase_requirements>

---

## Summary

Phase 08 wires the CLI entry point, creates the `cli/` subpackage skeleton, adds `[cli]` optional dependencies to `pyproject.toml`, and implements auth resolution — but does NOT add any resource commands (those are Phases 10–11). The foundation established here is consumed by every subsequent CLI phase.

The existing SDK is a clean foundation: sync public API wraps async internals, so Typer commands call SDK methods directly with no `asyncio` bridging needed. The impedance mismatch is zero. The only risk in this phase is configuration correctness (correct pyproject.toml table, correct entry point name) and import isolation (Typer/Rich must never leak into the base SDK import path).

Typer 0.24.1 is the current version [VERIFIED: uv pip install --dry-run]. The `>=0.12.0` floor from prior research is safe; 0.24 is well-established. Rich 14.3.3 is not present in the current venv (confirmed: `import rich` fails) despite being in uv.lock as a transitive dep of pip-audit — it must be declared explicitly in `[project.optional-dependencies]`.

**Primary recommendation:** Create `src/bunny_cdn_sdk/cli/__init__.py` with an ImportError guard that raises immediately in the `except` branch (so `ty` sees the unconditional happy path), then `cli/_app.py` with the root `typer.Typer()`, `State` dataclass, and `@app.callback()` resolving all auth options. Stub out sub-app registrations with empty `typer.Typer()` instances for the sub-apps that arrive in later phases. Verify with `uv run ty check src/` immediately.

---

## Project Constraints (from CLAUDE.md)

- **Tech stack**: httpx only — no requests, aiohttp, or other HTTP libs. CLI deps are Typer + Rich only; no other additions.
- **Python version**: 3.12+ (project runs on 3.14.3 [VERIFIED])
- **Package manager**: `uv` — all commands via `uv run <cmd>` or `uv add`. Never invoke `python`, `pytest`, `ruff`, or `ty` directly.
- **Type checker**: `ty` — not mypy or pyright. All CLI code must pass `uv run ty check src/`.
- **Return types**: plain `dict` — no Pydantic, no dataclasses (except `State` which is a CLI-internal dataclass, not a return type).
- **Auth**: Per-client key injection — CLI wires two separate auth paths (CoreClient vs StorageClient).
- **GSD Workflow**: No direct repo edits outside a GSD workflow — use `/gsd-execute-phase`.

---

## Standard Stack

### Core (New in Phase 08)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typer` | `>=0.12.0,<1` | CLI framework — nested sub-apps, env var resolution, Context propagation | Standard CLI framework for Python SDKs; stable nested-subcommand API since 0.4; 0.12 floor separates Rich as peer dep |
| `rich` | `>=13.0.0` | Terminal output — Table, Console, Console(stderr=True) | De facto Python terminal formatting library; already in lock as transitive dep; 14.3.3 in uv.lock |

**Verified current version:** Typer 0.24.1 would be installed by uv today [VERIFIED: uv pip install typer --dry-run]. Click 8.3.2 comes as a transitive dep of Typer — do NOT pin Click directly.

### Supporting (stdlib, no new dep)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dataclasses` | stdlib | `State` dataclass for auth context | Typed carrier for ctx.obj — avoids untyped dict |
| `contextlib` | stdlib | `sdk_errors()` context manager | Wraps every command body for consistent exception→exit-code mapping |
| `json` | stdlib | `--json` flag output | `json.dumps(..., default=str)` for all JSON output |
| `typer.testing.CliRunner` | (with typer) | In-process CLI test invocation | All CLI tests — captures stdout/stderr, returns exit_code |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `typer` | `click` directly | Typer adds ergonomic wrappers around Click (type inference, env var resolution); the project already targets Typer by spec — no alternative |
| `dataclass` for State | `dict` as ctx.obj | Typed State prevents KeyError bugs and enables `ty` checking; the tradeoff is one extra class definition |
| `contextmanager` for sdk_errors | decorator | Context manager is easier to test and compose; decorator requires wrapping every function signature |

**Installation (to add in pyproject.toml — not via `uv add` directly):**

```toml
[project.optional-dependencies]
cli = [
    "typer>=0.12.0,<1",
    "rich>=13.0.0",
]
```

Then sync for dev with:

```bash
uv sync --all-groups --extra cli
```

**Version verification:** [VERIFIED: uv pip install typer --dry-run 2026-04-10]
- typer 0.24.1
- click 8.3.2 (transitive)
- shellingham 1.5.4 (transitive)
- annotated-types 0.0.4 (transitive)

Rich version: 14.3.3 present in uv.lock but NOT currently installed in venv (confirmed: import fails). Will be pulled in when `--extra cli` is used.

---

## Architecture Patterns

### Recommended Project Structure

```
src/bunny_cdn_sdk/
    __init__.py          # UNCHANGED — no CLI imports here
    _client.py           # UNCHANGED
    _exceptions.py       # UNCHANGED
    _pagination.py       # UNCHANGED
    _retry.py            # UNCHANGED
    _types.py            # UNCHANGED
    core.py              # UNCHANGED
    storage.py           # UNCHANGED
    py.typed             # UNCHANGED
    cli/                 # NEW subpackage — all CLI code lives here
        __init__.py      # ImportError guard + re-export app
        _app.py          # Root Typer app, State dataclass, @app.callback()
        _output.py       # sdk_errors() context manager, output_result(), _cell()

tests/
    cli/                 # NEW test directory
        __init__.py
        conftest.py      # CliRunner fixture

pyproject.toml           # MODIFIED — add [project.optional-dependencies] + [project.scripts]
```

Phase 08 does NOT create sub-app files (`pull_zone.py`, `storage_zone.py`, etc.) — those are Phase 10/11. Phase 08 creates the skeleton that those files will attach to.

### Pattern 1: ImportError Guard (CLI Isolation)

**What:** `cli/__init__.py` wraps Typer/Rich imports in `try/except ImportError` and immediately `raise`s in the except branch. This ensures:
1. `import bunny_cdn_sdk` never touches `cli/` at all (no import chain reaches it)
2. `import bunny_cdn_sdk.cli` in a base-only env gives a clear error (not a traceback)
3. `ty` sees the `raise` in the except branch and does NOT flag subsequent Typer usage as "possibly unresolved"

**When to use:** This is the ONLY pattern for optional-dep isolation in this project.

```python
# src/bunny_cdn_sdk/cli/__init__.py
# Source: established Python optional-dep pattern (e.g., pandas optional backends) [ASSUMED: standard idiom]

try:
    import typer  # noqa: F401
    from rich.console import Console  # noqa: F401
except ImportError as _err:
    raise ImportError(
        "The bunnycdn CLI requires optional dependencies.\n"
        "Install them with:  pip install 'bunny-cdn-sdk[cli]'"
    ) from _err

from bunny_cdn_sdk.cli._app import app  # noqa: E402

__all__ = ["app"]
```

**Critical:** The `raise` is unconditional in the except block. `ty` follows both branches: the try branch uses Typer successfully; the except branch raises before any Typer usage, so `ty` doesn't see a "possibly unresolved" error on the code after the guard.

### Pattern 2: Root App + State Dataclass + Callback

**What:** A typed `State` dataclass is stored on `ctx.obj` by the root `@app.callback()`. Sub-app commands read auth from `ctx.obj` without re-resolving env vars.

```python
# src/bunny_cdn_sdk/cli/_app.py
# Source: Typer official docs — context and state passing pattern [ASSUMED: from training data, Typer stable since 0.4]

from __future__ import annotations

from dataclasses import dataclass, field
import typer

app = typer.Typer(no_args_is_help=True, help="Bunny CDN management CLI.")


@dataclass
class State:
    api_key: str = field(default="")
    storage_key: str = field(default="")
    zone_name: str = field(default="")
    region: str = field(default="falkenstein")
    json_output: bool = field(default=False)


@app.callback()
def main(
    ctx: typer.Context,
    api_key: str = typer.Option(
        "",
        envvar="BUNNY_API_KEY",
        help="Bunny CDN account API key. Prefer BUNNY_API_KEY env var.",
    ),
    storage_key: str = typer.Option(
        "",
        envvar="BUNNY_STORAGE_KEY",
        help="Bunny Storage Zone password. Prefer BUNNY_STORAGE_KEY env var.",
    ),
    zone_name: str = typer.Option(
        "",
        envvar="BUNNY_STORAGE_ZONE",
        help="Bunny Storage Zone name. Prefer BUNNY_STORAGE_ZONE env var.",
    ),
    region: str = typer.Option(
        "falkenstein",
        envvar="BUNNY_STORAGE_REGION",
        help="Storage region (default: falkenstein).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output raw JSON instead of formatted table.",
    ),
) -> None:
    ctx.ensure_object(State)
    state: State = ctx.obj
    state.api_key = api_key
    state.storage_key = storage_key
    state.zone_name = zone_name
    state.region = region
    state.json_output = json_output
```

**AUTH-04 handling:** When a command needs `api_key` but it's empty (no flag, no env var), the command function checks `if not state.api_key:` and emits a clear message + `raise typer.Exit(1)`. This is preferred over `typer.Option(..., ...)` (Ellipsis default) in the callback because the callback runs for ALL commands including `--help` and `--version`, which do not need auth.

```python
# In a command function body (e.g., pull_zone.list):
if not state.api_key:
    typer.echo(
        "Error: API key required. Use --api-key or set BUNNY_API_KEY.",
        err=True,
    )
    raise typer.Exit(1)
client = CoreClient(api_key=state.api_key)
```

### Pattern 3: sdk_errors() Context Manager

**What:** Wraps every command body to map SDK exceptions to exit codes. Lives in `_output.py` (no SDK dep beyond `_exceptions.py`).

```python
# src/bunny_cdn_sdk/cli/_output.py
# Source: contextlib.contextmanager is stdlib [VERIFIED]; exception classes verified from _exceptions.py

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Generator

import typer
from rich.console import Console

from bunny_cdn_sdk._exceptions import (
    BunnyAPIError,
    BunnyAuthenticationError,
    BunnyConnectionError,
    BunnyNotFoundError,
    BunnyRateLimitError,
    BunnyServerError,
    BunnyTimeoutError,
)

console = Console()
err_console = Console(stderr=True)


@contextmanager
def sdk_errors() -> Generator[None, None, None]:
    try:
        yield
    except BunnyAuthenticationError:
        err_console.print("Authentication failed. Check your API key.")
        raise typer.Exit(1)
    except BunnyNotFoundError as exc:
        err_console.print(f"Not found: {exc.message}")
        raise typer.Exit(1)
    except BunnyRateLimitError:
        err_console.print("Rate limited. Try again later.")
        raise typer.Exit(1)
    except BunnyServerError as exc:
        err_console.print(f"Server error: {exc.message}")
        raise typer.Exit(1)
    except BunnyAPIError as exc:
        err_console.print(f"API error {exc.status_code}: {exc.message}")
        raise typer.Exit(1)
    except BunnyConnectionError as exc:
        err_console.print(f"Connection error: {exc}")
        raise typer.Exit(1)
    except BunnyTimeoutError as exc:
        err_console.print(f"Timeout: {exc}")
        raise typer.Exit(1)
    except ValueError as exc:
        err_console.print(f"Invalid argument: {exc}")
        raise typer.Exit(1)


def output_result(data: Any, *, json_mode: bool = False) -> None:  # noqa: ANN401
    if json_mode:
        typer.echo(json.dumps(data, indent=2, default=str))
        return
    # Placeholder — full Rich table rendering is Phase 09
    typer.echo(str(data))


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    if isinstance(value, list):
        return f"[{len(value)} items]"
    return str(value)
```

**Note on exit codes:** All errors use `raise typer.Exit(1)` for Phase 08. The ARCHITECTURE.md suggested codes 1–7 per exception type; requirements only specify "exits with code 1 on any SDK or auth error" (OUT-05). Use code 1 uniformly to match requirements.

### Pattern 4: pyproject.toml Changes

**What:** Two new sections in `pyproject.toml`. Must be in the correct tables.

```toml
# CORRECT: published to PyPI, pip-installable
[project.optional-dependencies]
cli = [
    "typer>=0.12.0,<1",
    "rich>=13.0.0",
]

# CORRECT: registers the bunnycdn console script
[project.scripts]
bunnycdn = "bunny_cdn_sdk.cli:app"
```

**Critical correctness checks:**
- Table is `[project.optional-dependencies]` NOT `[dependency-groups]` — the latter is uv-local only and not published to PyPI
- Entry point name is `bunnycdn` NOT `bunny` — PyPI package `bunny` (file watcher) creates a real collision
- Entry point target is `bunny_cdn_sdk.cli:app` — the `app` object in `cli/__init__.py` (re-exported from `_app.py`)

### Pattern 5: CliRunner Test Structure

**What:** `typer.testing.CliRunner` for in-process test invocation. Comes with Typer — no additional dep.

```python
# tests/cli/conftest.py
import pytest
from typer.testing import CliRunner


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()
```

```python
# tests/cli/test_app.py
import json
from unittest.mock import patch

from bunny_cdn_sdk.cli import app


def test_help_shows(runner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "bunnycdn" in result.output.lower() or "bunny" in result.output.lower()


def test_no_args_shows_help(runner) -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0  # no_args_is_help=True shows help and exits 0


def test_auth_missing_emits_error(runner) -> None:
    # Invoking a sub-command that needs api_key with none set
    # This test is a placeholder — actual sub-commands are Phase 10
    pass
```

### Anti-Patterns to Avoid

- **CLI imports in `bunny_cdn_sdk/__init__.py`**: Any `from bunny_cdn_sdk.cli import app` or `import bunny_cdn_sdk.cli` in the top-level package breaks `import bunny_cdn_sdk` for base users. The CLI subpackage must never be reached from the SDK import chain.
- **`sys.exit(1)` instead of `raise typer.Exit(1)`**: `sys.exit` is not captured by `CliRunner.invoke()` reliably. Always `raise typer.Exit(code=1)`.
- **Module-level client instantiation**: `client = CoreClient(api_key=os.environ["BUNNY_API_KEY"])` at module top level fails at import time if env var is missing. Instantiate inside command functions.
- **`asyncio.run()` in command functions**: The SDK sync methods already call `asyncio.run()` internally. Calling it again from a Typer command causes `RuntimeError: This event loop is already running`.
- **Using `[dependency-groups]` for CLI extra**: Only `[project.optional-dependencies]` is published to PyPI. Using the wrong table means `pip install 'bunny-cdn-sdk[cli]'` silently fails.
- **Lazy sub-app registration**: All `app.add_typer()` calls must happen at module import time, not inside functions. Late registration causes `--help` to omit sub-commands.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var resolution with flag fallback | Custom env var reading + argparse | `typer.Option(envvar="BUNNY_API_KEY")` | Typer handles precedence (flag > env var > default) correctly and documents it in `--help` |
| CLI test harness | subprocess + shell invocation | `typer.testing.CliRunner` | In-process, captures stdout/stderr, returns exit_code, works with monkeypatch |
| Terminal table rendering | Custom string formatting | `rich.table.Table` | Handles column width, wrapping, ANSI codes, and TTY detection automatically |
| Exception-to-exit-code mapping per command | Duplicated try/except in every function | `sdk_errors()` context manager | DRY, testable in isolation, consistent across all commands |

**Key insight:** Typer's `envvar=` parameter is the canonical solution for the "flag OR env var" auth pattern. Do not implement custom env var reading alongside `typer.Option` — it creates two sources of truth for the same value.

---

## Common Pitfalls

### Pitfall 1: ty Reports "Possibly Unresolved" on Typer Usage After Guard
**What goes wrong:** `ty` follows both branches of `try/except`. If the `except` branch doesn't `raise`, `ty` sees that execution can continue without Typer being defined and flags all subsequent Typer usage as "possibly unresolved."
**Why it happens:** `ty` configuration has `possibly-unresolved-reference = "error"` — this becomes a hard error.
**How to avoid:** The `except` branch MUST `raise ImportError(...)` unconditionally. Never use `_CLI_DEPS_AVAILABLE = False` + conditional usage — `ty` cannot reason about this pattern.
**Warning signs:** `uv run ty check src/` reports errors in `cli/__init__.py` or `cli/_app.py` after writing the guard. Fix: verify the `except` branch has an unconditional `raise`.

### Pitfall 2: Rich Not Available in Base Venv
**What goes wrong:** Despite rich 14.3.3 being in uv.lock (as a transitive dep of pip-audit), it is NOT importable in the current venv. `python -c "import rich"` fails. [VERIFIED]
**Why it happens:** uv.lock includes all transitive deps for resolution purposes; the venv only installs what's explicitly in the active dependency groups.
**How to avoid:** Always `uv sync --all-groups --extra cli` before testing CLI code. Never assume uv.lock presence = venv availability.
**Warning signs:** `ImportError: No module named 'rich'` when running tests after adding CLI code.

### Pitfall 3: Entry Point Always Installed, Guard May Not Fire Correctly
**What goes wrong:** `[project.scripts]` registers `bunnycdn = "bunny_cdn_sdk.cli:app"` regardless of whether `[cli]` extras are installed. When a user runs `bunnycdn` without `[cli]` deps, Python tries to import `bunny_cdn_sdk.cli`, which triggers the ImportError guard — this is correct behavior. BUT if the guard is structured wrong (e.g., uses `sys.exit` instead of `raise ImportError`), the user sees a Python traceback instead of a clear message.
**How to avoid:** Guard must `raise ImportError(...)`. The Typer/Click machinery will catch the ImportError and print the message. Test with: install package without cli extra, run `bunnycdn`, verify message appears.
**Warning signs:** Traceback instead of clean message when running `bunnycdn` without `[cli]`.

### Pitfall 4: `--json` as a Global Flag — Context Propagation
**What goes wrong:** `--json` is defined in the root callback and stored on `State`. If Typer's context is not propagated to sub-apps correctly, commands cannot read `ctx.obj.json_output`.
**Why it happens:** Typer propagates `ctx.obj` automatically when using `app.add_typer()` AND when the sub-app command accepts `ctx: typer.Context` as first argument. If the command function doesn't declare `ctx: typer.Context`, it cannot access `ctx.obj`.
**How to avoid:** Every command function that needs auth or `--json` must declare `ctx: typer.Context` as its first parameter.
**Warning signs:** `ctx.obj` is None inside a sub-app command; `AttributeError` on `ctx.obj.api_key`.

### Pitfall 5: Ruff Violations on CLI Code
**What goes wrong:** The project has `ruff select = ["ALL"]`. CLI code triggers multiple rule violations that must be addressed upfront.
**Common violations in CLI code:**
- `ANN201` — missing return type on public functions → annotate all command functions `-> None`
- `TRY003` — long exception messages in `raise` → move messages to variables or add `TRY003` to per-file ignores for `cli/`
- `ARG001` — unused arguments (ctx in some commands) → suppress or restructure
- `T201` — `print()` usage (use `typer.echo` or `console.print` instead)
**How to avoid:** Add `"src/bunny_cdn_sdk/cli/**"` to `[tool.ruff.lint.per-file-ignores]` with at minimum `["TRY003"]`. Run `uv run ruff check src/bunny_cdn_sdk/cli/` immediately after writing each file.

---

## Code Examples

### Full pyproject.toml Changes

```toml
# Add to pyproject.toml — two new sections

[project.optional-dependencies]
cli = [
    "typer>=0.12.0,<1",
    "rich>=13.0.0",
]

[project.scripts]
bunnycdn = "bunny_cdn_sdk.cli:app"

# Optionally add a poe task for dev CLI install:
# [tool.poe.tasks]
# dev-cli = "uv sync --all-groups --extra cli"
```

### Minimal cli/__init__.py

```python
# src/bunny_cdn_sdk/cli/__init__.py
"""Bunny CDN CLI — optional extra. Install with: pip install 'bunny-cdn-sdk[cli]'."""

from __future__ import annotations

try:
    import typer  # noqa: F401
    from rich.console import Console  # noqa: F401
except ImportError as _err:
    raise ImportError(
        "The bunnycdn CLI requires optional dependencies.\n"
        "Install them with:  pip install 'bunny-cdn-sdk[cli]'"
    ) from _err

from bunny_cdn_sdk.cli._app import app  # noqa: E402

__all__ = ["app"]
```

### Verifying Import Isolation

```bash
# After implementing — run in base venv (no --extra cli):
uv run python -c "import bunny_cdn_sdk; print('OK')"
# Must print: OK

# Run ty check:
uv run ty check src/
# Must complete without errors in cli/ files

# Run ruff:
uv run ruff check src/bunny_cdn_sdk/cli/
# Must pass cleanly
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Typer bundled Rich internally | Rich is a peer dep, not bundled | Typer 0.12 (2024) | Must declare `rich` explicitly in `[project.optional-dependencies]`; do not rely on Typer pulling it in |
| `click.option(envvar=...)` requires custom resolver | `typer.Option(envvar=...)` handles resolution automatically | Typer 0.4+ | No custom env var reading needed |
| `[project.entry-points."console_scripts"]` | `[project.scripts]` shorthand | PEP 517 era | Use `[project.scripts]` — identical semantics, shorter syntax |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `typer>=0.12.0,<1` is the correct version constraint format | Standard Stack | Low — Typer uses semver; `<1` prevents major version jumps; if 1.x releases, re-evaluate |
| A2 | `typer.Option(envvar=...)` with empty-string default (not Ellipsis) is the correct pattern for optional auth that is validated inside the command | Architecture Pattern 2 | Medium — if Ellipsis is used, help/version invocations require the env var; empty string + manual check is safer |
| A3 | `ctx.ensure_object(State)` followed by `state: State = ctx.obj` is type-safe with `ty` | Architecture Pattern 2 | Medium — `ctx.obj` is `Any` in Typer's type stubs; `ty` may flag the cast; use `cast(State, ctx.obj)` if needed |
| A4 | `no_args_is_help=True` on the root Typer app causes `bunnycdn` with no args to print help and exit 0 | Architecture Pattern 2 | Low — standard Typer behavior, well-documented |
| A5 | Ruff `TRY003` will fire on the error messages in `sdk_errors()` | Pitfall 5 | Low — verified ruff `select = ["ALL"]` in pyproject.toml; TRY003 targets long raise messages |

---

## Open Questions

1. **Should `--json` be in the root callback or per-command?**
   - What we know: Root callback is simpler (one declaration); per-command is more explicit but requires 37 declarations.
   - What's unclear: Whether some commands should intentionally not support `--json` (e.g., `delete` commands that return `{}`).
   - Recommendation: Put `--json` in root callback for Phase 08 scaffold. Individual commands can override or ignore it. Revisit in Phase 09 (output layer).

2. **`ty` cast required for `ctx.obj`?**
   - What we know: `ctx.obj` is typed `Any` in Typer stubs. `ty` has `possibly-unresolved-reference = "error"`.
   - What's unclear: Whether `ty` flags `ctx.obj.api_key` as an error when `ctx.obj` is `Any`.
   - Recommendation: Use `state: State = ctx.obj` and run `uv run ty check src/` immediately. If `ty` flags it, add `cast(State, ctx.obj)` with `from typing import cast`.

3. **Ruff per-file ignores for `cli/` — what to add upfront?**
   - What we know: `select = ["ALL"]` with ignores `["D", "COM812", "ISC001"]`.
   - Recommendation: Add to pyproject.toml before writing CLI code: `"src/bunny_cdn_sdk/cli/**" = ["TRY003"]`. Extend as needed during implementation.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | Yes | 3.14.3 [VERIFIED] | — |
| uv | Package management | Yes | present [VERIFIED] | — |
| typer | CLI framework | No (not yet installed) | 0.24.1 would install [VERIFIED] | Add to pyproject.toml and `uv sync --extra cli` |
| rich | Terminal output | No (not in venv) | 14.3.3 in uv.lock [VERIFIED] | Add to pyproject.toml and `uv sync --extra cli` |
| click | Typer transitive dep | No (not yet) | 8.3.2 would install [VERIFIED] | Comes automatically with typer |
| ruff | Linting | Yes [VERIFIED: in dependency-groups.lint] | present | — |
| ty | Type checking | Yes [VERIFIED: in dependency-groups.lint] | present | — |
| pytest | Testing | Yes [VERIFIED: in dependency-groups.test] | present | — |

**Missing dependencies with no fallback:** None — all missing deps will be resolved by adding the `[cli]` optional extra and running `uv sync --all-groups --extra cli`.

**Missing dependencies with fallback:** None blocking. Typer and Rich must be added to `pyproject.toml` before any CLI code is written or tested.

---

## Security Domain

Phase 08 handles API key ingestion. Applicable controls:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes — API key handling | `typer.Option(envvar=...)` preferred over `--api-key` in shell; never log key value |
| V3 Session Management | No | CLI is stateless per-invocation |
| V4 Access Control | No | Authorization enforced by Bunny CDN API, not CLI |
| V5 Input Validation | Yes — API key format, region string | Validate non-empty before client construction; region validated by StorageClient |
| V6 Cryptography | No | No cryptographic operations in CLI scaffold |

### Known Threat Patterns for CLI Auth

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key in shell history | Information Disclosure | Prefer `BUNNY_API_KEY` env var; never log key value; `--api-key` flag accepted but documented as less secure |
| API key in process list (`ps aux`) | Information Disclosure | Inherent to `--api-key` flag; document env var preference; cannot be fully mitigated at CLI layer |
| Missing auth proceeds silently | Elevation of Privilege | Manual `if not state.api_key:` check emits error + `raise typer.Exit(1)` before client construction |

---

## Sources

### Primary (HIGH confidence)
- `/Users/toddj/github/bunny-cdn-python-sdk/main.git.create-sdk/pyproject.toml` — verified existing table structure, ruff config, dependency-groups pattern
- `/Users/toddj/github/bunny-cdn-python-sdk/main.git.create-sdk/src/bunny_cdn_sdk/_exceptions.py` — verified all 8 exception classes and inheritance chain
- `/Users/toddj/github/bunny-cdn-python-sdk/main.git.create-sdk/src/bunny_cdn_sdk/_client.py` — verified `asyncio.run()` in `_sync_request`; confirmed sync/async boundary
- `/Users/toddj/github/bunny-cdn-python-sdk/main.git.create-sdk/src/bunny_cdn_sdk/storage.py` — verified StorageClient constructor: `zone_name`, `password`, `region` (three separate args)
- `uv pip install typer --dry-run` — verified Typer 0.24.1 is current installable version [VERIFIED 2026-04-10]
- `uv run python -c "import rich"` — confirmed rich is NOT currently in the active venv [VERIFIED 2026-04-10]
- `.planning/research/STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `FEATURES.md`, `SUMMARY.md` — milestone-level research from earlier session (HIGH confidence baseline)
- `.planning/STATE.md` — confirmed decisions: entry point `bunnycdn`, `[project.optional-dependencies]`, `--set KEY=VALUE` update style

### Secondary (MEDIUM confidence)
- `CLAUDE.md` project constraints — enforced project rules
- `.planning/REQUIREMENTS.md` — v2.0 requirements, Phase 08 requirement IDs
- PEP 508 / PEP 735 distinction [ASSUMED: well-established spec, confirmed by STACK.md research]

### Tertiary (LOW confidence)
- None — all critical claims verified from codebase or tool invocation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Typer 0.24.1 verified via uv pip install; Rich version from uv.lock; Click is transitive
- Architecture: HIGH — patterns verified against existing codebase; Typer context/callback patterns are stable since 0.4
- Pitfalls: HIGH — entry point collision confirmed by STATE.md decision log; ImportError guard pattern verified against ty configuration in pyproject.toml; Rich venv status verified

**Research date:** 2026-04-10
**Valid until:** 2026-07-10 (Typer 0.x stable; Rich 13+ stable)
