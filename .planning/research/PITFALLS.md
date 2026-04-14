# Domain Pitfalls: Adding a Typer CLI to bunny-cdn-sdk

**Domain:** Optional Typer-based CLI on an existing Python SDK with async internals
**Researched:** 2026-04-10
**Confidence:** HIGH — grounded in Typer/Click/Rich source code, pyproject.toml mechanics, and project-specific constraints

---

## Critical Pitfalls

Mistakes that cause runtime breakage, polluted installs, or broken CLI behavior.

---

### Pitfall 1: Module-Level Typer/Rich Imports in `__init__.py` or SDK Modules

**What goes wrong:** If `import typer` or `from rich.table import Table` appears at module scope in any file reachable from `bunny_cdn_sdk/__init__.py`, then `import bunny_cdn_sdk` raises `ImportError` for users who installed `bunny-cdn-sdk` (base) without `[cli]`. The SDK silently breaks for everyone who does not opt into the CLI extra.

**Why it happens:** The CLI module is co-located with the SDK in the same package. Any import that reaches the CLI module — even transitively — will trigger Typer/Rich imports at install time.

**Consequences:** Breaks the core value proposition. Users get `ModuleNotFoundError: No module named 'typer'` when calling `from bunny_cdn_sdk import CoreClient`. Impossible to use the SDK without the CLI extra.

**Prevention:**
- Keep CLI code in a dedicated subpackage: `bunny_cdn_sdk/cli/` or `bunny_cdn_sdk/_cli.py`.
- Never import from the CLI subpackage in `__init__.py` or any non-CLI module.
- Use a guard at the top of every CLI module:

```python
# bunny_cdn_sdk/cli/__init__.py
try:
    import typer
    from rich.console import Console
except ImportError as e:
    raise ImportError(
        "CLI dependencies not installed. Run: pip install 'bunny-cdn-sdk[cli]'"
    ) from e
```

- This guard fires only when the CLI module is explicitly imported (i.e., when the `bunny` entry point runs), not during normal SDK usage.

**Detection:** Run `python -c "import bunny_cdn_sdk"` in an environment where only the base package is installed (no `[cli]`). It must succeed without error.

**Phase:** CLI scaffold phase (first CLI phase). Must be enforced from day one.

---

### Pitfall 2: `asyncio.run()` Conflicts — Nested Event Loop

**What goes wrong:** The SDK's sync public API uses `asyncio.run()` internally (see `_client.py`: `_sync_request` calls `asyncio.run(self._request(...))`). In most CLI scenarios this works fine, but it breaks in two situations:

1. If a user runs the CLI from within an already-running event loop (Jupyter, async test runner with `anyio`/`asyncio` mode). `asyncio.run()` raises `RuntimeError: This event loop is already running`.
2. If the test suite for the CLI itself uses `pytest-anyio` or `pytest-asyncio` in async mode — the CliRunner invokes the command synchronously, which calls `asyncio.run()`, which conflicts.

**Why it happens:** `asyncio.run()` creates a new event loop, but Python only allows one running event loop per thread. Typer/Click CliRunner is synchronous, so it runs in the main thread alongside any existing loop.

**Consequences:** CLI tests fail with `RuntimeError` when run inside async test infrastructure. Users calling CLI from Jupyter get an error.

**Prevention:**
- Do not use async test runners for CLI tests. Use Typer's `CliRunner` synchronously — the SDK's sync-wrapping of async already handles the event loop correctly.
- In `pytest.ini_options`, do NOT set `asyncio_mode = "auto"` globally. Use `@pytest.mark.asyncio` only on SDK-internal async tests that directly test coroutines.
- If future test infrastructure needs async, scope the event loop per-test, not globally.
- The current SDK design (`asyncio.run()` per call) is safe for the CLI use case as long as tests stay synchronous.

**Detection:** Run `uv run pytest tests/cli/` — if any CLI test uses `async def`, replace with sync `def`.

**Phase:** CLI test phase. Review test structure before writing any async CLI tests.

---

### Pitfall 3: Exit Code Semantics — `raise typer.Exit(code=1)` vs `sys.exit(1)`

**What goes wrong:** Using `sys.exit(1)` in a Typer command raises `SystemExit`, which Typer/Click's `CliRunner` catches and converts to `result.exit_code`. However, raw `sys.exit()` bypasses Typer's exception-handling hook, and in certain contexts (particularly when a `typer.Option` callback raises) it can cause confusing test failures where the exit code is not what was expected.

More critically: catching exceptions and calling `sys.exit(1)` without printing a message leaves the CLI silent on error. Users get no feedback about what went wrong.

**The correct pattern:**
```python
import typer

app = typer.Typer()

@app.command()
def list_pull_zones(api_key: str = typer.Option(..., envvar="BUNNY_API_KEY")) -> None:
    try:
        client = CoreClient(api_key=api_key)
        zones = client.list_pull_zones()
        # ... render output
    except BunnyAuthenticationError:
        typer.echo("Error: Invalid API key", err=True)
        raise typer.Exit(code=1)
    except BunnySDKError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
```

**Why `raise typer.Exit(code=1)` over `sys.exit(1)`:**
- `CliRunner.invoke()` catches `typer.Exit` and exposes it as `result.exit_code` — testable without inspecting `SystemExit`.
- Typer can introspect `Exit` for documentation and shell completion purposes.
- `sys.exit(1)` in a command that also has `--help` causes confusing interactions with Click's help system.

**Consequences of wrong pattern:** Tests pass locally but fail in CI because `result.exit_code` is 0 when `sys.exit` was swallowed by CliRunner incorrectly. Or tests are brittle, catching `SystemExit` explicitly.

**Prevention:** Always use `raise typer.Exit(code=1)` for error exits. Always print the error message to `stderr` via `typer.echo(..., err=True)` or `Console(stderr=True)` before exiting.

**Detection:** Any `sys.exit` call in `bunny_cdn_sdk/cli/` should be treated as a bug. Add a ruff rule: the `SYS003` / `S603` family does not cover this, but a grep in CI is sufficient.

**Phase:** CLI scaffold phase and CLI test phase.

---

### Pitfall 4: JSON Serialization of Non-Serializable Dict Values

**What goes wrong:** The SDK returns plain `dict` from `response.json()`. Bunny CDN API responses sometimes include values that are already Python objects after JSON parsing (nested dicts, lists, `None`). However, `json.dumps(response_dict)` fails when the dict contains any non-JSON-serializable type. The most common culprit in Bunny API responses is `datetime`-like strings that have already been parsed by a middleware (not a concern here since we return raw `response.json()`), but also:
- `None` — serializes fine as `null`
- Integers larger than `2^53` — lose precision in JavaScript but serialize correctly in Python
- The real risk: if any future SDK method ever stores `httpx.Response` objects or `datetime` objects in the returned dict, `json.dumps()` will raise `TypeError`

**Specific risk for this project:** `StorageClient` returns file listing dicts that contain date strings (ISO 8601). These serialize correctly. But `--json` output for `StorageClient.list()` returns a list, not a dict — callers must wrap in `json.dumps(list_result, ...)`.

**Prevention:**
```python
import json
import sys

def _output_json(data: object) -> None:
    """Render any SDK return value as JSON to stdout."""
    try:
        typer.echo(json.dumps(data, indent=2, default=str))
    except TypeError as e:
        typer.echo(f"Error: Cannot serialize response to JSON: {e}", err=True)
        raise typer.Exit(code=1)
```

Using `default=str` as a fallback serializer prevents crashes: any non-serializable value becomes its string representation. This is acceptable for a CLI output path — the goal is human-readable JSON, not round-trippable data.

**Consequences of missing this:** CLI crashes with an unhandled `TypeError` traceback for specific endpoints. Users see a Python exception instead of a helpful error message.

**Phase:** CLI output/formatting phase.

---

### Pitfall 5: Rich Table Rendering of None Values and Nested Dicts

**What goes wrong:** Rich's `Table.add_row()` accepts `str | Text | ...` per cell. If a dict value is `None`, passing it directly raises a `TypeError` or renders as the string "None" silently. Nested dict values (e.g., `{"PullZone": {"Id": 1, "Name": "zone"}}` nested inside another resource dict) render as `{'Id': 1, 'Name': 'zone'}` — an ugly Python repr that is not useful in a terminal table.

**Why it happens:** Bunny CDN API responses are inconsistently structured. Some fields are nullable (`None` after JSON parse). Some fields are nested objects (e.g., storage zone stats embedded in a pull zone response).

**Prevention:**
```python
def _cell(value: object) -> str:
    """Coerce any dict value to a safe table cell string."""
    if value is None:
        return ""
    if isinstance(value, dict):
        # Flatten nested dicts to key=value pairs
        return ", ".join(f"{k}={v}" for k, v in value.items())
    if isinstance(value, list):
        return f"[{len(value)} items]"
    return str(value)
```

Apply `_cell()` to every value before passing to `table.add_row()`. Do not rely on Rich's default coercion.

**Long string handling:** Pull zone `OriginUrl` and DNS zone names can be 100+ characters. Use `Column(no_wrap=False, overflow="fold")` or truncate with `Text(value, overflow="ellipsis")` for fixed-width terminal output. Do not use `no_wrap=True` globally — it causes horizontal scrolling in narrow terminals.

**Consequences of missing this:** CLI crashes with `TypeError` on any endpoint that returns nullable fields. Or output is unusable Python reprs that users copy-paste and get confused by.

**Phase:** CLI output/formatting phase.

---

## Moderate Pitfalls

Issues that produce incorrect behavior or poor UX but do not crash the CLI.

---

### Pitfall 6: Entry Point Name `bunny` — Collision Risk

**What goes wrong:** The name `bunny` as a console script entry point may collide with other tools a user has installed. As of April 2026, there is a PyPI package `bunny` (a simple file watcher) that could install a `bunny` script. If both packages are installed, the one installed last wins — silently.

**Why it happens:** Python entry points from `[project.scripts]` are just executable scripts in the venv's `bin/` directory. Last writer wins.

**Prevention:**
- Name the entry point `bunnycdn` instead of `bunny` — more specific, far less likely to collide.
- Alternatively use `bcdn` as a shorter but unique name.
- Do NOT use `bunny` — the collision risk is real and confusing to users who have the file-watcher installed.

**Recommendation:** Use `bunnycdn` as the entry point name. Document it clearly in the README. This is the correct decision for an SDK that is not the primary/only "bunny" tool a developer might use.

**Detection:** Check PyPI for `bunny` and any `bunny-*` package with a console script before finalizing the name.

**Phase:** CLI scaffold phase (entry point decision is final before publishing).

---

### Pitfall 7: Click/Typer Version Constraints Too Loose

**What goes wrong:** Typer wraps Click. As of Typer 0.12+, Typer requires Click >= 8.x. If a user's environment has a tool that pins `click<8` (e.g., some older Flask CLI setups, or the `aws-cli` v1), installing `bunny-cdn-sdk[cli]` will either:
- Fail with a resolver conflict (if uv/pip catches the incompatibility), or
- Silently downgrade/upgrade click and break the other tool

**Why it happens:** Click 7 and Click 8 have incompatible APIs. Typer 0.12+ does not support Click 7. The user's environment may already have a Click version pinned by another tool.

**Prevention:**
- In `pyproject.toml`, pin `typer>=0.12,<1` (not just `typer`). This makes the constraint explicit and resolver-visible.
- Do not pin Click directly — let Typer's own dependency on Click resolve it. Adding a redundant `click>=8` constraint can cause over-constraining.
- In documentation, note that the `[cli]` extra requires Click 8, and users with `click<8` pinned in their environment will see a conflict.

**Detection:** Test `pip install 'bunny-cdn-sdk[cli]' 'click==7.1.2'` — should fail at resolve time, not at runtime.

**Phase:** CLI scaffold phase (pyproject.toml configuration).

---

### Pitfall 8: Testing — CliRunner Does Not Test Real Terminal Output

**What goes wrong:** `typer.testing.CliRunner` (which wraps `click.testing.CliRunner`) captures output but does NOT render Rich markup — it captures plain text. Rich's `Console` detects that stdout is not a real TTY and disables ANSI codes and rich rendering. Tables render as plain text without borders.

**Specific consequences:**
1. Testing that a Rich table was rendered correctly by inspecting `result.output` for ANSI escape codes does not work — CliRunner strips them.
2. Testing that a table has the right number of rows by counting separators does not work.
3. `Console(force_terminal=True)` in the CLI module breaks CliRunner tests by forcing ANSI output that CliRunner doesn't expect.

**Correct testing approach:**
```python
from typer.testing import CliRunner
from bunny_cdn_sdk.cli import app

runner = CliRunner()

def test_list_pull_zones_json(monkeypatch):
    """Test --json flag; does not depend on Rich rendering."""
    monkeypatch.setenv("BUNNY_API_KEY", "test-key")
    # Mock the CoreClient method
    with patch("bunny_cdn_sdk.cli.core.CoreClient") as MockClient:
        MockClient.return_value.list_pull_zones.return_value = [{"Id": 1, "Name": "zone"}]
        result = runner.invoke(app, ["pull-zone", "list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["Name"] == "zone"

def test_list_pull_zones_table(monkeypatch):
    """Test table output; check presence of key content, not formatting."""
    monkeypatch.setenv("BUNNY_API_KEY", "test-key")
    with patch("bunny_cdn_sdk.cli.core.CoreClient") as MockClient:
        MockClient.return_value.list_pull_zones.return_value = [{"Id": 1, "Name": "myzone"}]
        result = runner.invoke(app, ["pull-zone", "list"])
    assert result.exit_code == 0
    assert "myzone" in result.output  # Content present, not format
```

**What to mock:** Always mock the SDK client, not the HTTP layer, in CLI tests. The CLI layer's job is to call the client correctly and render output — not to make HTTP requests. Use `unittest.mock.patch` to replace `CoreClient` and `StorageClient` constructors.

**Prevention:** Write CLI tests that assert on content presence (not format), and assert on exit codes. Use `--json` flag tests to verify data correctness (JSON is easy to parse and assert on).

**Phase:** CLI test phase.

---

### Pitfall 9: `pyproject.toml` — Optional Deps Must Use `[project.optional-dependencies]` Not `[dependency-groups]`

**What goes wrong:** The project currently uses `[dependency-groups]` (PEP 735) for dev/test/lint groups. This is correct for dev tooling. However, CLI extras that users install must be declared in `[project.optional-dependencies]`, not `[dependency-groups]`. Using `[dependency-groups]` for CLI would mean `pip install 'bunny-cdn-sdk[cli]'` fails — the extras would not be published to PyPI.

**Why it happens:** `[dependency-groups]` is a local development convention (uv-specific). It does not appear in the built wheel's metadata. `[project.optional-dependencies]` is the PEP 508 standard that gets embedded in wheel metadata and is resolvable by any pip/installer.

**Prevention:**
```toml
# CORRECT — published to PyPI, installable via pip install 'bunny-cdn-sdk[cli]'
[project.optional-dependencies]
cli = ["typer>=0.12,<1", "rich>=13"]

# WRONG — only visible to uv locally, not in the published wheel
[dependency-groups]
cli = ["typer>=0.12,<1", "rich>=13"]
```

Note: Rich is already in the project venv (version 14.3.3) as a transitive dep of pip-audit tooling, but it is NOT a declared project dependency. It must be explicitly declared in `[project.optional-dependencies]` for the CLI extra.

**Detection:** `uv build && pip install dist/*.whl && pip install 'bunny-cdn-sdk[cli]'` — the `[cli]` extras must be resolvable. If using `[dependency-groups]`, the `[cli]` extra does not appear in the wheel.

**Phase:** CLI scaffold phase (pyproject.toml setup).

---

### Pitfall 10: `--api-key` as a Plain CLI Option — Secret Leakage in Shell History

**What goes wrong:** If the CLI accepts `--api-key sk-live-xxxxx`, this key appears in:
- `~/.bash_history` / `~/.zsh_history`
- `ps aux` output while the process runs
- CI logs if not masked
- Shell autocomplete history

**Prevention:**
- Accept `--api-key` only as a fallback. Prefer `BUNNY_API_KEY` envvar (set via Typer's `envvar="BUNNY_API_KEY"` parameter).
- Never log the key value. In error messages, print `"Invalid API key"` not `f"Key {api_key} was rejected"`.
- In `typer.Option()`, use `hide_input=True` if prompting — but do not prompt for the key by default; the envvar is safer.

```python
api_key: str = typer.Option(
    ...,
    envvar="BUNNY_API_KEY",
    help="Bunny CDN API key. Prefer setting BUNNY_API_KEY env var.",
)
```

**Phase:** CLI scaffold phase (auth design).

---

## Minor Pitfalls

Issues that cause confusion or minor bugs but are easy to fix.

---

### Pitfall 11: Typer App Structure — Nested Subcommands Must Be Added Before First Invocation

**What goes wrong:** Typer apps with subcommands (`app.add_typer(sub_app, name="pull-zone")`) must have all sub-apps added at module import time, before any `app()` call. If sub-apps are added conditionally or lazily (inside a function), `--help` omits them and command routing fails silently.

**Prevention:** Build the full app structure at module level:
```python
# bunny_cdn_sdk/cli/__init__.py
app = typer.Typer(name="bunnycdn")
app.add_typer(pull_zone_app, name="pull-zone")
app.add_typer(storage_zone_app, name="storage-zone")
# ... etc.
```

**Phase:** CLI scaffold phase.

---

### Pitfall 12: Ruff Violations in CLI Code — ANN and TRY Rules

**What goes wrong:** The project has `select = ["ALL"]` in ruff config. Typer commands decorated with `@app.command()` must have type annotations on all parameters for Typer to infer CLI types. However, return type is always `None` for commands — ruff's `ANN201` (missing return type annotation on public function) will fire if not annotated. `TRY003` (long messages in exception raises) fires for helpful error strings.

**Prevention:**
- Annotate all Typer command functions with `-> None`.
- For `TRY003`: create exception classes or move error strings to constants. Or add `TRY003` to the per-file ruff ignore list for `src/bunny_cdn_sdk/cli/**`.
- The existing `tests/**` per-file-ignores pattern should be extended to `src/bunny_cdn_sdk/cli/**` for `TRY003` if needed.

**Phase:** CLI scaffold phase (configure ruff ignores before writing CLI code).

---

### Pitfall 13: `ty` Type Checking — Optional Import Pattern Triggers Errors

**What goes wrong:** The `try: import typer except ImportError` guard pattern (Pitfall 1's fix) causes `ty` to report errors when typer types are used after the guard block. `ty` sees the `except ImportError: raise ImportError(...)` branch and may flag subsequent uses of `typer.Typer()` as "possibly unresolved" since `ty` follows both branches of the try/except.

**Prevention:**
- Use `TYPE_CHECKING` guard for type annotations:
```python
from __future__ import annotations
from typing import TYPE_CHECKING

try:
    import typer
    from rich.console import Console
    from rich.table import Table
    _CLI_DEPS_AVAILABLE = True
except ImportError:
    _CLI_DEPS_AVAILABLE = False
    ...

if TYPE_CHECKING:
    import typer  # noqa: F811
```

- Or, more simply: since the CLI subpackage is only ever imported when the `bunny` entry point runs (not during SDK usage), the `try/except` guard can raise immediately on `ImportError` and the rest of the module can use typer unconditionally. `ty` will see the `raise` in the except branch and not flag subsequent usage.

**Phase:** CLI scaffold phase. Check `uv run ty check src/` after writing the import guard.

---

## Phase-Specific Warnings Summary

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| CLI scaffold: `pyproject.toml` | `[dependency-groups]` instead of `[project.optional-dependencies]` for CLI extra | Use `[project.optional-dependencies]` only |
| CLI scaffold: entry point naming | `bunny` collides with PyPI `bunny` file-watcher | Use `bunnycdn` as entry point name |
| CLI scaffold: Typer/Rich import | Module-level import leaks into base SDK | Lazy import in CLI subpackage only; test with base-only install |
| CLI scaffold: Typer version | Click 7 vs Click 8 conflicts in user envs | Pin `typer>=0.12,<1` |
| CLI scaffold: Typer app structure | Sub-apps added lazily break routing | Add all sub-apps at module level |
| CLI auth design | API key in shell history | Prefer envvar; use `envvar="BUNNY_API_KEY"` in `typer.Option` |
| CLI output: JSON | Non-serializable values in dict output | Use `json.dumps(..., default=str)` |
| CLI output: Rich tables | `None` values and nested dicts in table cells | `_cell()` helper to coerce all values to strings |
| CLI output: Rich tables | Long strings break table layout | Use `overflow="fold"` on wide columns |
| CLI testing | CliRunner strips Rich ANSI; tests break if checking formatting | Assert content not format; use `--json` for data assertions |
| CLI testing | Async conflict with `asyncio.run()` | Keep all CLI tests synchronous |
| CLI testing | `sys.exit()` not testable via CliRunner | Always use `raise typer.Exit(code=1)` |
| Ruff config | `ANN201` and `TRY003` fire on command functions | Annotate `-> None`; add per-file ignores for CLI dir |
| `ty` checking | Optional import guard triggers "possibly unresolved" | Use `raise` in except branch so `ty` sees unconditional path |

---

## Sources

- Project source code: `src/bunny_cdn_sdk/_client.py` — confirmed `asyncio.run()` usage pattern
- Project config: `pyproject.toml` — confirmed `[dependency-groups]` structure, ruff `select = ["ALL"]`
- Project venv: Rich 14.3.3 installed as transitive dep (not declared in project deps) — confirmed not in `[project.optional-dependencies]`
- `python-sdk-patterns` skill — asyncio task lifecycle, SDK architecture constraints
- `modern-python` skill — `[project.optional-dependencies]` vs `[dependency-groups]` distinction
- Typer source: Click wrapper architecture (HIGH confidence — well-established in Typer docs)
- Rich 14.3.3 source: `table.py` — Column API, rendering behavior (HIGH confidence — inspected directly)
- Click CliRunner behavior: strips ANSI codes, catches SystemExit (HIGH confidence — foundational Click behavior)
