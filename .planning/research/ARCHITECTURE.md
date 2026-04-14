# Architecture Patterns: Typer CLI Integration

**Domain:** Optional Typer CLI layer on top of an existing sync Python SDK
**Project:** bunny-cdn-sdk v2.0
**Researched:** 2026-04-10
**Overall confidence:** HIGH — patterns verified against existing codebase; Typer/Rich patterns are stable and well-established

---

## Recommended Architecture

The CLI is a thin, optional presentation layer. It instantiates SDK clients, calls sync SDK methods (no asyncio needed), and formats results. It never contains business logic.

```
bunny_cdn_sdk/
    cli/                        # NEW subpackage — optional, gated behind [cli] extra
        __init__.py             # exports `app` (the root Typer app)
        _app.py                 # root app definition + callback (auth option resolution)
        _output.py              # shared Rich table renderer + --json mode
        pull_zone.py            # `bunny pull-zone` sub-app
        storage_zone.py         # `bunny storage-zone` sub-app
        dns_zone.py             # `bunny dns-zone` sub-app
        video_library.py        # `bunny video-library` sub-app
        storage.py              # `bunny storage` sub-app
```

The main `bunny_cdn_sdk/__init__.py` is NOT modified. The CLI is not importable from the top-level package — users reach it only via the `bunny` console script entry point or `python -m bunny_cdn_sdk.cli`.

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `cli/_app.py` | Root Typer app; global `--api-key` / `--storage-key` options; Typer context carrier | All sub-apps via `app.add_typer()` |
| `cli/_output.py` | Rich table rendering; `--json` raw output; exit-code-friendly error printing | All sub-app command functions |
| `cli/pull_zone.py` | Commands for `bunny pull-zone list/get/create/delete/purge-cache` | `_app.py` context, `_output.py`, `CoreClient` |
| `cli/storage_zone.py` | Commands for `bunny storage-zone list/get/create/delete` | Same pattern |
| `cli/dns_zone.py` | Commands for `bunny dns-zone list/get/create/delete` | Same pattern |
| `cli/video_library.py` | Commands for `bunny video-library list/get/create/delete` | Same pattern |
| `cli/storage.py` | Commands for `bunny storage upload/download/delete/list` | `_app.py` context, `_output.py`, `StorageClient` |

---

## Package Layout — Detailed

### New Files (all new — no existing files modified except pyproject.toml)

```
src/bunny_cdn_sdk/cli/__init__.py
src/bunny_cdn_sdk/cli/_app.py
src/bunny_cdn_sdk/cli/_output.py
src/bunny_cdn_sdk/cli/pull_zone.py
src/bunny_cdn_sdk/cli/storage_zone.py
src/bunny_cdn_sdk/cli/dns_zone.py
src/bunny_cdn_sdk/cli/video_library.py
src/bunny_cdn_sdk/cli/storage.py
tests/cli/__init__.py
tests/cli/conftest.py
tests/cli/test_pull_zone.py
tests/cli/test_storage_zone.py
tests/cli/test_dns_zone.py
tests/cli/test_video_library.py
tests/cli/test_storage.py
tests/cli/test_output.py
```

### Modified Files

```
pyproject.toml
    — add [project.optional-dependencies] cli = ["typer>=0.12", "rich>=13"]
    — add [project.scripts] bunny = "bunny_cdn_sdk.cli:app"
    — add cli optional deps to dev dependency-groups so CI covers them
```

`src/bunny_cdn_sdk/__init__.py` — NOT modified. The top-level public API does not expose CLI.

---

## Optional Dependency Guard Pattern

Typer and Rich must not be imported at module top-level in any SDK module. The entire `cli/` subpackage is the isolation boundary — nothing outside `cli/` imports from it.

Within `cli/__init__.py`, guard the import so that installing the SDK without `[cli]` extras produces a helpful error rather than an `ImportError` traceback:

```python
# src/bunny_cdn_sdk/cli/__init__.py
try:
    import typer  # noqa: F401
    import rich   # noqa: F401
except ImportError as e:
    raise ImportError(
        "The bunny-cdn-sdk CLI requires optional dependencies. "
        "Install them with: pip install 'bunny-cdn-sdk[cli]'"
    ) from e

from bunny_cdn_sdk.cli._app import app  # noqa: E402

__all__ = ["app"]
```

This means:
- `import bunny_cdn_sdk` — always works, zero overhead
- `import bunny_cdn_sdk.cli` without extras — raises `ImportError` with a clear message
- `bunny` console script — Typer's entry point only resolves after `[cli]` is installed, so the error surfaces cleanly

The guard lives ONLY in `cli/__init__.py`. Sub-modules (`_app.py`, `pull_zone.py`, etc.) import Typer/Rich directly — they are only ever reached after `cli/__init__.py` has already verified the deps.

---

## Auth Wiring — Typer Context Pattern

Auth credentials are resolved once per invocation and passed down through Typer's context object. This avoids re-resolving env vars or `--api-key` flags in every command function.

```python
# cli/_app.py
import os
from dataclasses import dataclass, field
import typer

app = typer.Typer(no_args_is_help=True)

@dataclass
class State:
    api_key: str = field(default="")
    storage_key: str = field(default="")

@app.callback()
def main(
    ctx: typer.Context,
    api_key: str = typer.Option(
        "", envvar="BUNNY_API_KEY", help="Bunny CDN account API key."
    ),
    storage_key: str = typer.Option(
        "", envvar="BUNNY_STORAGE_KEY", help="Bunny Storage Zone password."
    ),
) -> None:
    ctx.ensure_object(State)
    ctx.obj.api_key = api_key
    ctx.obj.storage_key = storage_key
```

Sub-app command functions receive `ctx: typer.Context` and read `ctx.obj` to get credentials. Client instantiation happens inside the command function — not at module level, not in a sub-app callback.

```python
# cli/pull_zone.py
import typer
from bunny_cdn_sdk import CoreClient
from bunny_cdn_sdk.cli._app import State
from bunny_cdn_sdk.cli._output import output_result

pull_zone_app = typer.Typer(no_args_is_help=True, name="pull-zone")

@pull_zone_app.command("list")
def list_pull_zones(
    ctx: typer.Context,
    search: str = typer.Option(None, help="Filter by name."),
    json: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    state: State = ctx.obj
    client = CoreClient(api_key=state.api_key)
    result = client.list_pull_zones(search=search)
    output_result(result, json_mode=json)
```

**Rationale for per-command instantiation:** SDK clients are lightweight (they create an httpx.AsyncClient on first use). Instantiating per-command is safe, avoids connection sharing across unrelated commands, and makes each command independently testable. A shared `CoreClient` in context would complicate teardown and test isolation.

---

## Calling Sync SDK Methods from Typer

The existing SDK methods are already synchronous (`_sync_request` wraps `asyncio.run()`). Typer command functions are also synchronous. The call is a direct function call — no `asyncio.run()`, no threading, no special handling needed.

```python
# In a Typer command — this is all that's needed:
result = client.list_pull_zones()
```

The `asyncio.run()` is already buried inside `_sync_request` in `_client.py`. Typer does not intercept or wrap the event loop. This means there is zero impedance between Typer commands and SDK methods.

---

## Error Mapping — SDK Exceptions to CLI Exit Codes

Typer exits with code 0 on success. CLI commands must catch SDK exceptions and call `raise typer.Exit(code=N)` after printing a user-friendly message via `typer.echo` (or Rich). Do NOT let raw tracebacks reach users.

Recommended mapping:

| Exception | Exit Code | Message |
|-----------|-----------|---------|
| `BunnyAuthenticationError` | 1 | "Authentication failed: check your API key." |
| `BunnyNotFoundError` | 2 | "Not found: {exc.message}" |
| `BunnyRateLimitError` | 3 | "Rate limited. Try again later." |
| `BunnyServerError` | 4 | "Bunny CDN server error: {exc.message}" |
| `BunnyAPIError` (catch-all) | 5 | "API error {exc.status_code}: {exc.message}" |
| `BunnyConnectionError` | 6 | "Connection error: {exc}" |
| `ValueError` (bad region, etc.) | 7 | "Invalid argument: {exc}" |

Implementation: a shared `handle_sdk_error()` context manager or decorator in `cli/_output.py` that wraps every command body. This keeps error handling DRY and testable.

```python
# cli/_output.py
from contextlib import contextmanager
from typing import Generator
import typer
from bunny_cdn_sdk._exceptions import (
    BunnyAuthenticationError, BunnyNotFoundError, BunnyRateLimitError,
    BunnyServerError, BunnyAPIError, BunnyConnectionError,
)

@contextmanager
def sdk_errors() -> Generator[None, None, None]:
    try:
        yield
    except BunnyAuthenticationError:
        typer.echo("Authentication failed: check your API key.", err=True)
        raise typer.Exit(1)
    except BunnyNotFoundError as exc:
        typer.echo(f"Not found: {exc.message}", err=True)
        raise typer.Exit(2)
    except BunnyRateLimitError:
        typer.echo("Rate limited. Try again later.", err=True)
        raise typer.Exit(3)
    except BunnyServerError as exc:
        typer.echo(f"Bunny CDN server error: {exc.message}", err=True)
        raise typer.Exit(4)
    except BunnyAPIError as exc:
        typer.echo(f"API error {exc.status_code}: {exc.message}", err=True)
        raise typer.Exit(5)
    except BunnyConnectionError as exc:
        typer.echo(f"Connection error: {exc}", err=True)
        raise typer.Exit(6)
    except ValueError as exc:
        typer.echo(f"Invalid argument: {exc}", err=True)
        raise typer.Exit(7)
```

Usage in a command:

```python
@pull_zone_app.command("list")
def list_pull_zones(ctx: typer.Context, ...) -> None:
    state: State = ctx.obj
    with sdk_errors():
        client = CoreClient(api_key=state.api_key)
        result = client.list_pull_zones()
    output_result(result, ...)
```

---

## Output Layer — Rich Tables and --json Mode

`cli/_output.py` owns all output formatting. The pattern:

```python
import json as json_module
from typing import Any
import typer
from rich.console import Console
from rich.table import Table

console = Console()

def output_result(data: dict | list, *, json_mode: bool = False) -> None:
    if json_mode:
        typer.echo(json_module.dumps(data, indent=2))
        return
    # Rich table rendering — inspect data shape and render accordingly
    _render_table(data)
```

Key decisions:
- `--json` flag is per-command (not global). Some commands' output is not tabular (e.g., `delete` which returns `{}`).
- Rich writes to stdout. Errors always go to `typer.echo(..., err=True)` (stderr).
- The `Console()` instance is module-level in `_output.py` so it can be patched in tests.

---

## Sub-App Registration

```python
# cli/_app.py (after sub-apps are defined in their modules)
from bunny_cdn_sdk.cli.pull_zone import pull_zone_app
from bunny_cdn_sdk.cli.storage_zone import storage_zone_app
from bunny_cdn_sdk.cli.dns_zone import dns_zone_app
from bunny_cdn_sdk.cli.video_library import video_library_app
from bunny_cdn_sdk.cli.storage import storage_app

app.add_typer(pull_zone_app)
app.add_typer(storage_zone_app)
app.add_typer(dns_zone_app)
app.add_typer(video_library_app)
app.add_typer(storage_app)
```

Each sub-app is a `typer.Typer(name="pull-zone", no_args_is_help=True)` instance defined in its own module. This gives `bunny pull-zone --help`, `bunny pull-zone list`, etc.

---

## Data Flow

```
User invokes: bunny pull-zone list --search foo

1. Entry point: pyproject.toml [project.scripts] → bunny_cdn_sdk.cli:app
2. cli/__init__.py → ImportError guard → imports _app.py
3. Typer parses argv: routes to pull_zone_app, "list" command
4. app.callback() fires: resolves --api-key / BUNNY_API_KEY → stores in ctx.obj (State)
5. pull_zone.list_pull_zones(ctx, search="foo", json=False) called
6. Instantiates CoreClient(api_key=ctx.obj.api_key)
7. Calls client.list_pull_zones(search="foo") → plain dict returned
8. output_result(dict, json_mode=False) → Rich table to stdout
9. Typer exits 0
```

On error:
```
7a. client.list_pull_zones() raises BunnyNotFoundError
7b. sdk_errors() context manager catches it
7c. typer.echo("Not found: ...", err=True) → stderr
7d. raise typer.Exit(2) → process exits 2
```

---

## Build Order

Dependencies flow in this order:

1. **`pyproject.toml`** — add `[cli]` optional dep group and `[project.scripts]` entry point first. Required before any CLI code can be installed/tested.

2. **`cli/_output.py`** — no SDK dependency other than `_exceptions.py`. Shared by all sub-apps. Build and test this first (unit-testable with captured output, no HTTP).

3. **`cli/_app.py`** — root app + callback + State dataclass + sub-app registration stubs. Can be skeleton-built (no sub-apps registered yet) and tested for `--help` output.

4. **`cli/__init__.py`** — ImportError guard + `from ._app import app`. Trivial, but must be written before any entry point works.

5. **Core sub-apps** (pull_zone, storage_zone, dns_zone, video_library) — all follow identical pattern; build in any order. Each can be tested independently by mocking `CoreClient`.

6. **Storage sub-app** (`cli/storage.py`) — depends on `StorageClient`; slightly different auth wiring (`--storage-key`, `--zone-name`, `--region`). Build last among sub-apps.

7. **Integration tests** — `tests/cli/` — use `typer.testing.CliRunner` to invoke the CLI end-to-end with mocked SDK clients.

---

## Testing Strategy

Use `typer.testing.CliRunner` from the `typer[all]` package. It invokes the Typer app in-process, captures stdout/stderr, and returns an exit code — no subprocess needed.

Mock at the SDK client boundary, not at the HTTP boundary. CLI tests should not know about httpx.

```python
# tests/cli/conftest.py
from typer.testing import CliRunner
import pytest

@pytest.fixture
def runner():
    return CliRunner()
```

```python
# tests/cli/test_pull_zone.py
from unittest.mock import patch, MagicMock
from bunny_cdn_sdk.cli import app

def test_list_pull_zones(runner):
    mock_result = {"Items": [{"Id": 1, "Name": "zone-1"}], "TotalItems": 1, ...}
    with patch("bunny_cdn_sdk.cli.pull_zone.CoreClient") as MockClient:
        MockClient.return_value.list_pull_zones.return_value = mock_result
        result = runner.invoke(app, ["pull-zone", "list", "--api-key", "test-key"])
    assert result.exit_code == 0
    assert "zone-1" in result.stdout
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: CLI imports in SDK __init__.py
**What:** `from bunny_cdn_sdk.cli import app` in the top-level `__init__.py`
**Why bad:** Forces `ImportError` on every SDK user who hasn't installed `[cli]` extras. Breaks the "thin optional layer" promise.
**Instead:** CLI is only reachable via the `bunny` console script or explicit `import bunny_cdn_sdk.cli`.

### Anti-Pattern 2: Module-level client instantiation in sub-apps
**What:** `client = CoreClient(api_key=os.environ["BUNNY_API_KEY"])` at module top-level
**Why bad:** Client created at import time — fails on import if env var is missing, prevents testing, creates connection pooling issues.
**Instead:** Instantiate `CoreClient` inside each command function, reading from `ctx.obj`.

### Anti-Pattern 3: asyncio.run() in CLI commands
**What:** `result = asyncio.run(client._request(...))` directly in a command
**Why bad:** SDK methods are already sync. Calling `asyncio.run()` on top of methods that already use it internally will raise `RuntimeError: This event loop is already running` in some contexts.
**Instead:** Call SDK public methods directly — they are sync.

### Anti-Pattern 4: Letting SDK exceptions propagate uncaught
**What:** No try/except around SDK calls in commands
**Why bad:** Users see raw Python tracebacks with httpx internals. Exit code is always 1 (unhandled exception). Impossible to test exit codes.
**Instead:** Wrap every command body in `with sdk_errors():`.

### Anti-Pattern 5: One monolithic cli.py file
**What:** All CLI commands in `src/bunny_cdn_sdk/cli.py` (single file)
**Why bad:** Grows to 1000+ lines. Hard to test sub-app isolation. Circular import risk.
**Instead:** `cli/` subpackage with one file per resource group.

---

## Scalability Considerations

| Concern | Current (v2.0) | If Many Commands Added |
|---------|----------------|----------------------|
| Command discovery | `app.add_typer()` per sub-app, explicit | Same pattern; add new sub-app file |
| Auth resolution | Single `State` dataclass in callback | Same; add new credential fields |
| Output formatting | `_output.py` centralized | Add new renderer functions, not new modules |
| Test isolation | `CliRunner` + patch `CoreClient` | Same pattern per sub-app |

---

## Confidence Notes

- **Typer nested sub-apps via `app.add_typer()`** — HIGH confidence. This is Typer's documented, stable pattern since 0.4. No version-specific concerns.
- **`typer.Context` / `ctx.obj` for shared state** — HIGH confidence. Documented pattern, used by the official Typer tutorial for multi-command apps.
- **`typer.testing.CliRunner`** — HIGH confidence. Stable API, part of Typer's public surface.
- **`[cli]` optional extras in pyproject.toml** — HIGH confidence. Standard PEP 508 / PEP 517 mechanism, fully supported by uv.
- **Typer version** — Recommend `typer>=0.12`. Typer 0.12 (released 2024) added significant improvements to help formatting and sub-app naming. Rich 14.x is already in the lockfile as a transitive dep, so no version conflict risk.
- **ImportError guard pattern** — HIGH confidence. Standard Python idiom for optional dependencies (used by pandas, SQLAlchemy, and others for optional backends).

---

## Sources

- Existing codebase: `src/bunny_cdn_sdk/` — verified directly
- `.planning/PROJECT.md` — v2.0 milestone goals
- `docs/HLD.md` — package structure, client architecture
- Typer documentation patterns (knowledge cutoff August 2025, Typer 0.12.x stable)
- uv.lock — Rich 14.3.3 already present; Typer not yet added
