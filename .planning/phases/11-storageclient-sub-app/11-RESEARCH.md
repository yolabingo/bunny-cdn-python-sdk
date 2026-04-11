# Phase 11: StorageClient Sub-App — Research

**Researched:** 2026-04-11
**Domain:** Typer CLI sub-app for StorageClient file operations (list/upload/download/delete)
**Confidence:** HIGH

---

## Summary

Phase 11 adds a `bunnycdn storage` sub-app wiring StorageClient's four operations to the CLI. The sub-app is architecturally parallel to the CoreClient sub-apps delivered in Phase 10, with one key distinction: it uses a different auth model (zone_name + storage_key + region instead of api_key). All three storage auth fields are already captured in the `State` dataclass and the global `@app.callback()` — no changes to `_app.py` are needed for auth.

The four operations have meaningfully different output types: `list` returns a list of file/directory dicts suitable for `output_result()`, while `upload` returns an empty dict on success (204), `download` returns raw bytes (which must be written to disk, not printed), and `delete` returns None. Upload and download require filesystem I/O (reading a local file for upload, writing bytes to disk for download) which the CoreClient sub-apps never needed. CliRunner tests for upload/download must use `tmp_path` or `tempfile` for real file fixtures since Typer arguments are filesystem paths.

**Primary recommendation:** Create `src/bunny_cdn_sdk/cli/_storage.py` following the exact `_pull_zone.py` pattern, wire it into `_app.py` as `name="storage"`, and test in `tests/cli/test_storage.py`. Upload reads the local file in binary mode and passes bytes to `StorageClient.upload()`. Download calls `StorageClient.download()` and writes the returned bytes to the local path. Use `typer.echo()` for upload/download success messages; use `output_result()` for list.

---

## Phase Requirements

<phase_requirements>

| ID | Description | Research Support |
|----|-------------|------------------|
| ST-01 | `bunnycdn storage list [path]` lists files/directories at a storage path | Verified: `StorageClient.list(path="/")` returns `list[dict]` with ObjectName, Length, IsDirectory, LastChanged fields — maps directly to `output_result()` with curated columns |
| ST-02 | `bunnycdn storage upload <local-path> <remote-path>` uploads a local file | Verified: `StorageClient.upload(path, data: bytes | BinaryIO)` — CLI must `open(local_path, "rb")` and pass bytes |
| ST-03 | `bunnycdn storage download <remote-path> <local-path>` downloads a storage file | Verified: `StorageClient.download(path)` returns `bytes` — CLI must `open(local_path, "wb").write(result)` |
| ST-04 | `bunnycdn storage delete <remote-path>` deletes with confirmation prompt | Verified: `StorageClient.delete(path)` returns None — pattern identical to pull-zone delete minus the get-first step |

</phase_requirements>

---

## Standard Stack

No new dependencies. Phase 11 uses only libraries already installed by Phase 08's `[cli]` extra.

### Core (all existing)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typer | (existing) | CLI framework, Argument/Option, confirmation | Already wired; consistent with all sub-apps |
| rich | (existing) | Table output via `output_result()` | Already wired in `_output.py` |
| bunny_cdn_sdk.storage.StorageClient | local | Storage file operations | The SDK class this sub-app wraps |

**Installation:** No new installs needed.

---

## Architecture Patterns

### Recommended File Structure

```
src/bunny_cdn_sdk/cli/
├── _app.py            # Add: import storage_app + app.add_typer(storage_app, name="storage")
├── _storage.py        # NEW: storage sub-app (list/upload/download/delete)
└── ... (existing files unchanged)

tests/cli/
├── test_storage.py    # NEW: CliRunner tests for storage commands
└── ... (existing files unchanged)
```

### Pattern 1: Auth Validation (from existing sub-apps)

Storage auth uses `state.zone_name`, `state.storage_key`, and `state.region`. All three are already on the `State` dataclass and populated by `@app.callback()` via `BUNNY_STORAGE_ZONE`, `BUNNY_STORAGE_KEY`, and `BUNNY_STORAGE_REGION` env vars.

**Auth guard pattern for storage commands:**
```python
# Source: verified from _pull_zone.py and _app.py
state = cast("State", ctx.obj)
if not state.zone_name or not state.storage_key:
    err_console.print(
        "Missing storage auth. Use --zone-name/--storage-key "
        "or set BUNNY_STORAGE_ZONE/BUNNY_STORAGE_KEY."
    )
    raise typer.Exit(1)
```

Note: `region` has a default of `"falkenstein"` in `State` so it is always present. Only `zone_name` and `storage_key` must be non-empty.

### Pattern 2: StorageClient Instantiation

```python
# Source: verified from storage.py StorageClient.__init__
client = StorageClient(
    zone_name=state.zone_name,
    password=state.storage_key,
    region=state.region,
)
```

The `StorageClient` constructor takes `zone_name`, `password` (the storage key), and `region`. The `password` arg name is important — the CLI `storage_key` field maps to `password`.

### Pattern 3: list command

```python
# Source: verified from _pull_zone.py + storage.py
_COLUMNS = ["ObjectName", "Length", "IsDirectory", "LastChanged"]

@storage_app.command("list")
def list_files(
    ctx: typer.Context,
    path: str = typer.Argument("/", help="Storage path to list (default: zone root)"),
) -> None:
    """List files and directories at a storage path."""
    ...
    with sdk_errors():
        client = StorageClient(...)
        files = client.list(path)
        output_result(files, columns=_COLUMNS, json_mode=state.json_output)
```

The `path` argument is optional with a default of `"/"`. `output_result()` handles empty list (prints empty table with headers) and list of dicts (prints Rich table).

### Pattern 4: upload command

```python
@storage_app.command("upload")
def upload_file(
    ctx: typer.Context,
    local_path: str = typer.Argument(..., help="Local file path to upload"),
    remote_path: str = typer.Argument(..., help="Destination path in storage zone"),
) -> None:
    """Upload a local file to storage."""
    import os
    ...
    with sdk_errors():
        if not os.path.isfile(local_path):
            raise ValueError(f"Local file not found: {local_path!r}")
        client = StorageClient(...)
        with open(local_path, "rb") as fh:
            client.upload(remote_path, fh.read())
        typer.echo(f"Uploaded {local_path!r} -> {remote_path!r}")
```

Key decisions:
- Use `fh.read()` (bytes) rather than passing the file handle, because `StorageClient.upload()` calls `data.read()` internally anyway for BinaryIO, and full-buffer is safe for CLI use where progress bars are out of scope.
- `os.path.isfile()` check provides a clear error before making a network call.
- `ValueError` is caught by `sdk_errors()` and printed to stderr with exit code 1.
- Output is a plain `typer.echo()` success message, not `output_result()`, since there is no tabular data to display.

### Pattern 5: download command

```python
@storage_app.command("download")
def download_file(
    ctx: typer.Context,
    remote_path: str = typer.Argument(..., help="Storage path to download"),
    local_path: str = typer.Argument(..., help="Local destination path"),
) -> None:
    """Download a storage file to local filesystem."""
    ...
    with sdk_errors():
        client = StorageClient(...)
        data = client.download(remote_path)
        with open(local_path, "wb") as fh:
            fh.write(data)
        typer.echo(f"Downloaded {remote_path!r} -> {local_path!r}")
```

Key decisions:
- If `local_path` already exists, overwrite silently (consistent with CLI conventions; no prompt).
- Parent directory is expected to exist — do not create intermediate directories.
- Write error (permission denied, no such directory) will surface as an unhandled `OSError`. This can be wrapped in `sdk_errors()` if desired — but `sdk_errors()` only catches `ValueError` and SDK exceptions, not `OSError`. The simplest approach: let `OSError` propagate (Typer catches it and prints a traceback) OR wrap write in a try/except and re-raise as `ValueError`. Decision: wrap the write in `try/except OSError` and `raise ValueError(str(exc))` so `sdk_errors()` handles it cleanly.

### Pattern 6: delete command

```python
@storage_app.command("delete")
def delete_file(
    ctx: typer.Context,
    remote_path: str = typer.Argument(..., help="Storage path to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a file from storage (prompts for confirmation)."""
    ...
    with sdk_errors():
        if not yes:
            typer.confirm(f"Delete {remote_path!r} from storage zone?", abort=True)
        client = StorageClient(...)
        client.delete(remote_path)
        typer.echo(f"Deleted {remote_path!r}.")
```

Unlike pull-zone delete, there is no pre-flight GET (no `client.get_file()` exists on StorageClient). Confirmation prompt uses the remote path as the displayed identifier.

### Pattern 7: Wiring into _app.py

```python
# Source: verified from _app.py existing pattern
from bunny_cdn_sdk.cli._storage import storage_app
app.add_typer(storage_app, name="storage")
```

This is the only change to `_app.py`.

### Anti-Patterns to Avoid

- **Importing State at module level in _storage.py:** All sub-apps use deferred `from bunny_cdn_sdk.cli._app import State` inside command bodies to avoid circular imports. The module-level `storage_app = typer.Typer(...)` is fine; `State` import is not.
- **Using `output_result()` for upload/download:** These operations return no tabular data. `typer.echo()` with a success message is correct.
- **Passing BinaryIO handle to upload:** While `StorageClient.upload()` accepts `BinaryIO`, using `fh.read()` (bytes) in the CLI avoids potential issues with async transport. The SDK docs note BinaryIO is read via `.read()` anyway.
- **Checking `state.region` for None:** `State.region` defaults to `"falkenstein"` in the dataclass — it is always a non-empty string. Only check `zone_name` and `storage_key`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Auth validation | Custom try/except | `sdk_errors()` context manager | Already handles all SDK exception types + ValueError |
| Table rendering | Custom Rich table | `output_result(columns=_COLUMNS, ...)` | Column pruning, JSON mode, empty list handling all built in |
| Storage file I/O | Custom streaming | `open(path, "rb").read()` + `StorageClient.upload()` | SDK already handles BinaryIO; full-buffer is appropriate for CLI |
| StorageClient auth | Custom header building | `StorageClient(zone_name, password, region)` constructor | Encodes Basic auth header internally |

---

## Common Pitfalls

### Pitfall 1: Circular Import Between _storage.py and _app.py

**What goes wrong:** If `_storage.py` imports `State` or `storage_app` at module level from `_app.py`, and `_app.py` imports `storage_app` from `_storage.py`, Python raises `ImportError: cannot import name`.

**Why it happens:** `_app.py` imports all sub-app Typer instances at module level. If those modules import back from `_app.py` at module level, the circular dependency manifests at import time.

**How to avoid:** Import `State` inside each command function body (deferred import), not at module level. All existing sub-apps (pull_zone, storage_zone, dns_zone, video_library) follow this exact pattern — mirror it exactly.

**Warning signs:** `ImportError` when running `bunnycdn --help` or during test collection.

### Pitfall 2: StorageClient constructor uses `password` not `storage_key`

**What goes wrong:** The `StorageClient.__init__` parameter is named `password`, not `storage_key`. Passing `storage_key=state.storage_key` as a keyword arg raises `TypeError`.

**How to avoid:** Use positional args or the correct keyword: `StorageClient(state.zone_name, state.storage_key, region=state.region)`.

### Pitfall 3: CliRunner cannot write real files by default

**What goes wrong:** `download` writes to `local_path` which may be a real filesystem path in tests. CliRunner doesn't sandbox filesystem access.

**How to avoid:** In tests, use `tmp_path` (pytest fixture) to create a writable temp path. For upload tests, create a real temp file with content and pass its path.

**Test pattern:**
```python
def test_storage_download_success(runner, tmp_path) -> None:
    dest = tmp_path / "file.txt"
    with patch("bunny_cdn_sdk.storage.StorageClient") as MockClient:
        MockClient.return_value.download.return_value = b"hello"
        result = runner.invoke(app, [
            "--zone-name", "z", "--storage-key", "k",
            "storage", "download", "remote/file.txt", str(dest)
        ])
    assert result.exit_code == 0
    assert dest.read_bytes() == b"hello"
```

### Pitfall 4: download OSError not caught by sdk_errors()

**What goes wrong:** If the local path is unwritable, `open(local_path, "wb")` raises `OSError` which is not caught by `sdk_errors()` (which only catches SDK exceptions and `ValueError`).

**How to avoid:** Wrap the `open()` and `fh.write()` in `try/except OSError as exc: raise ValueError(str(exc))`. This re-routes OS errors through `sdk_errors()`'s `ValueError` handler, printing to stderr and exiting 1 cleanly.

### Pitfall 5: upload local_path not found — uncaught before SDK call

**What goes wrong:** If `local_path` doesn't exist and the file-not-found check is omitted, `open()` raises `FileNotFoundError` (an `OSError` subclass) which bypasses `sdk_errors()`.

**How to avoid:** Explicitly check with `os.path.isfile(local_path)` and raise `ValueError` before opening. This provides a cleaner error message than a raw exception traceback.

### Pitfall 6: Missing env vars for storage auth in CliRunner tests

**What goes wrong:** CliRunner does not inherit shell env vars by default (mix_stderr=False). Tests that rely on env vars silently fail auth checks.

**How to avoid:** Always pass `--zone-name` and `--storage-key` explicitly in test invocations, or use `runner.invoke(app, [...], env={"BUNNY_STORAGE_ZONE": "z", "BUNNY_STORAGE_KEY": "k"})`. The explicit flag approach is simpler and used by all existing tests.

---

## Code Examples

### Full _storage.py structure (verified pattern)

```python
# Source: verified from _pull_zone.py, _storage_zone.py patterns + storage.py API
"""Storage file CLI sub-app."""

from __future__ import annotations

import os
from typing import cast

import typer

from bunny_cdn_sdk.cli._output import err_console, output_result, sdk_errors

storage_app = typer.Typer(no_args_is_help=True, help="Manage Bunny CDN storage files.")
_COLUMNS = ["ObjectName", "Length", "IsDirectory", "LastChanged"]


@storage_app.command("list")
def list_files(
    ctx: typer.Context,
    path: str = typer.Argument("/", help="Storage path (default: zone root)"),
) -> None:
    """List files and directories at a storage path."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.storage import StorageClient

    state = cast("State", ctx.obj)
    if not state.zone_name or not state.storage_key:
        err_console.print(
            "Missing storage auth. Use --zone-name/--storage-key "
            "or set BUNNY_STORAGE_ZONE/BUNNY_STORAGE_KEY."
        )
        raise typer.Exit(1)
    with sdk_errors():
        client = StorageClient(state.zone_name, state.storage_key, region=state.region)
        files = client.list(path)
        output_result(files, columns=_COLUMNS, json_mode=state.json_output)
```

### CliRunner test for upload (temp file fixture)

```python
# Source: verified pattern combining pytest tmp_path + test_pull_zone.py mock pattern
def test_storage_upload_success(runner, tmp_path) -> None:
    src = tmp_path / "file.txt"
    src.write_bytes(b"hello")
    with patch("bunny_cdn_sdk.storage.StorageClient") as MockClient:
        MockClient.return_value.upload.return_value = {}
        result = runner.invoke(app, [
            "--zone-name", "z", "--storage-key", "k",
            "storage", "upload", str(src), "remote/file.txt"
        ])
    assert result.exit_code == 0
    assert "Uploaded" in result.output
```

### CliRunner test for missing auth

```python
def test_storage_list_missing_auth(runner) -> None:
    result = runner.invoke(app, ["storage", "list"])
    assert result.exit_code == 1
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| N/A (new sub-app) | Mirror _pull_zone.py pattern | No deviation needed |

The Typer sub-app pattern is stable across phases 08–10. No changes to the pattern for phase 11.

---

## Open Questions

1. **Should download overwrite silently or prompt?**
   - What we know: No existing pull-zone command uses overwrite logic; delete-with-confirm is the only prompt pattern.
   - What's unclear: Whether users expect a confirmation if `local_path` already exists.
   - Recommendation: Overwrite silently (consistent with Unix conventions; `cp`, `curl -o` all overwrite). Add a note in the command docstring.

2. **Should list support a `--json` flag independently or inherit global?**
   - What we know: All existing list commands use `state.json_output` which is set by the global `--json` flag.
   - Resolution: Use `state.json_output` (global flag). No per-command JSON override needed.

3. **How many test cases per command?**
   - What we know: pull-zone tests cover: success, error, json, missing-auth, plus command-specific cases (confirmed prompt, aborted prompt, not found).
   - Recommendation: Match the pull-zone test density. Storage commands need: success, error, json (list only), missing-auth, plus upload-file-not-found, download-writes-bytes, delete-confirmed, delete-aborted.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 11 is a pure code addition (new CLI module + tests). No external tools, services, or CLI utilities beyond the existing project stack are required.

---

## Validation Architecture

nyquist_validation is explicitly `false` in `.planning/config.json`. Section omitted per instructions.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes — storage auth | `StorageClient(zone_name, password, region)` constructor handles Basic auth header |
| V4 Access Control | yes — auth guard | Check `state.zone_name` and `state.storage_key` before constructing client; exit 1 on missing |
| V5 Input Validation | yes — local path | `os.path.isfile()` check before open; OSError re-raised as ValueError |
| V6 Cryptography | no | Storage password is passed to SDK; no client-side crypto |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via remote_path | Tampering | StorageClient builds URL via `_build_url()` which strips leading slash — no traversal risk above zone root |
| Credentials in output | Information Disclosure | Never echo `state.storage_key` in any success or error message |
| Overwriting arbitrary local files | Tampering | Download writes to the user-specified `local_path` — no extra mitigation needed (user controls the path) |

---

## Sources

### Primary (HIGH confidence)
- `storage.py` — read directly: `StorageClient.__init__`, `upload()`, `download()`, `delete()`, `list()` signatures verified [VERIFIED: codebase]
- `_app.py` — read directly: `State` dataclass fields (`storage_key`, `zone_name`, `region`), `@app.callback()` option wiring verified [VERIFIED: codebase]
- `_pull_zone.py` — read directly: established sub-app pattern verified [VERIFIED: codebase]
- `_output.py` — read directly: `output_result()`, `sdk_errors()`, `err_console` API verified [VERIFIED: codebase]
- `tests/cli/test_pull_zone.py` — read directly: test structure, mock patterns, CliRunner usage verified [VERIFIED: codebase]
- `tests/cli/conftest.py` — read directly: `runner` fixture verified [VERIFIED: codebase]
- `tests/test_storage.py` — read directly: StorageClient return types verified (upload returns `{}`, download returns `bytes`, list returns `list[dict]`, delete returns `None`) [VERIFIED: codebase]
- Bunny CDN Storage API — fetched `docs.bunny.net/reference/get_{storagezonename}-{path}`: confirmed list response fields (`ObjectName`, `Length`, `IsDirectory`, `LastChanged`, `Guid`, etc.) [CITED: docs.bunny.net]

### Secondary (MEDIUM confidence)
- StorageClient internal behavior for upload with BinaryIO: verified from `storage.py` line 139 (`payload: bytes = data.read() if hasattr(data, "read") else data`) [VERIFIED: codebase]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Silent overwrite on download (no prompt if local_path exists) | Architecture Patterns / Pattern 5 | User confusion if they expect a prompt; easy to add `--yes` flag if needed |
| A2 | `_COLUMNS = ["ObjectName", "Length", "IsDirectory", "LastChanged"]` is the right column set | Architecture Patterns / Pattern 3 | Output may show less useful data; adjust by changing the list — no structural impact |

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are existing project dependencies
- Architecture: HIGH — pattern is directly observable in 4 existing sub-apps and verified from source
- StorageClient API: HIGH — read directly from storage.py and test_storage.py
- State/auth wiring: HIGH — read directly from _app.py
- Pitfalls: HIGH — derived from direct code inspection (circular import pattern, constructor param name, OSError gap)

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stable codebase, no external API dependencies introduced)
