# Phase 5 Context: Quality & Coverage

**Generated:** 2026-04-10 (from assumptions — tech debt scope fully known from v1.0 audit)
**Phase goal:** Close all four v1.0 coverage gaps so every existing module reaches 100% and the public package surface has a smoke test.

---

## Requirements In Scope

| ID | Description |
|----|-------------|
| QUAL-01 | `BunnyAPIError.__str__` covered by at least one test |
| QUAL-02 | Context manager cleanup path (`aclose()` when `_client_owner=True`) covered |
| QUAL-03 | `list_single_page()` removed or wired — no orphaned export |
| QUAL-04 | At least one test imports from `bunny_cdn_sdk` (public surface smoke test) |

---

## Precise Gap Analysis (from v1.0 audit + live code)

### QUAL-01 — `BunnyAPIError.__str__` (line 41 of `_exceptions.py`)

```python
def __str__(self) -> str:
    return f"HTTP {self.status_code}: {self.message}"   # LINE 41 — UNCOVERED
```

**Root cause:** `test_exceptions.py` asserts `.status_code` attribute but never calls `str(exc)`.
**Fix:** Add `assert str(exc_info.value) == "HTTP 401: error"` to `test_authentication_error` (or any exception test). One line change to an existing test.

---

### QUAL-02 — Context manager lifecycle (lines 57–58, 62–63, 72 of `_client.py`)

```python
# __aexit__ — line 57–58 UNCOVERED
if self._client_owner:          # line 57
    await self._client.aclose() # line 58

# __enter__ — lines 62–63 UNCOVERED
asyncio.run(self.__aenter__())  # line 62
return self                     # line 63

# __exit__ — line 72 UNCOVERED
asyncio.run(self.__aexit__(exc_type, exc_val, exc_tb))  # line 72
```

**Root cause:** All 58 existing tests use `make_base_client(handler)` which injects `AsyncClient` → sets `_client_owner=False` → `aclose()` branch never taken. `__enter__`/`__exit__` never called (tests use `_sync_request` directly).

**Important constraints:**
- `__aenter__` just `return self` — trivially safe
- `__aexit__` calls `aclose()` only when `_client_owner=True` (no injection)
- Sync `__enter__` calls `asyncio.run(self.__aenter__())` — creates a new event loop; safe in sync pytest tests
- Sync `__exit__` calls `asyncio.run(self.__aexit__(...))` — creates a new event loop; safe in sync pytest tests
- `asyncio.run` CANNOT be called from within a running event loop — but all current tests are synchronous so this is fine

**Fix approach:**
```python
# Async context manager test — wrap in asyncio.run
import asyncio
async def _run():
    async with _BaseClient("key"):
        pass
asyncio.run(_run())

# Sync context manager test — direct
with _BaseClient("key"):
    pass
```

No MockTransport needed for these tests — they just verify the client opens and closes without error.

---

### QUAL-03 — `list_single_page` orphan (`_pagination.py` lines 39–54)

**Root cause:** Phase 2 (plan 02-02) added `list_single_page()` anticipating use by `list_*` methods, but Phase 3 (plan 03-01) implemented all `list_*` methods by calling `_sync_request()` directly — the helper was never imported or called.

**Current state of `_pagination.py`:**
```python
__all__ = ["pagination_iterator", "list_single_page"]  # list_single_page is dead
```

**`core.py` import:** Only imports `pagination_iterator` — `list_single_page` never imported.

**Resolution:** Remove `list_single_page` entirely:
1. Delete function body (lines 39–54 of `_pagination.py`)
2. Remove from `__all__` 
3. Verify no imports reference it in `core.py`, `storage.py`, tests, or `__init__.py`

Removal is the right call: the function is a trivial one-liner (`return await fetch_page(page)`) that adds zero value over calling `fetch_page(page)` directly.

---

### QUAL-04 — Public surface smoke test

**Root cause:** All 58 tests import from `bunny_cdn_sdk._client`, `bunny_cdn_sdk.core`, `bunny_cdn_sdk.storage` — zero tests exercise the package root.

**Fix:** Create `tests/test_public_surface.py`:
```python
def test_public_imports():
    from bunny_cdn_sdk import CoreClient, StorageClient, BunnyAPIError
    assert CoreClient is not None
    assert StorageClient is not None
    assert BunnyAPIError is not None
```

This also serves as a regression test against INFRA-10 (the TYPE_CHECKING guard that broke `v1.0` before the post-audit fix).

---

## File Map

| File | Action | Lines affected |
|------|--------|---------------|
| `tests/test_exceptions.py` | Add `str()` assertion to existing test | +1 line |
| `tests/test_client_lifecycle.py` | Create new — context manager tests | +30 lines |
| `tests/test_public_surface.py` | Create new — smoke test | +10 lines |
| `src/bunny_cdn_sdk/_pagination.py` | Remove `list_single_page` function + `__all__` entry | -17 lines |

---

## Decisions

- **QUAL-03 resolution: removal** — `list_single_page` has no callers; removal is cleaner than wiring it to a dead path in `core.py`. Requirements allow either path.
- **Context manager tests: no MockTransport** — tests don't need HTTP interception; they only verify enter/exit lifecycle
- **QUAL-01 fix: amend existing test** — adding one assertion to `test_authentication_error` is minimal and targeted; no new test function needed
- **QUAL-04: new file** — `test_public_surface.py` keeps the smoke test isolated and clearly named

---

## Coverage Baseline (v1.0)

```
_exceptions.py     18 stmts   1 miss   94%   ← QUAL-01
_client.py         57 stmts  10 miss   82%   ← QUAL-02
_pagination.py     16 stmts   1 miss   94%   ← QUAL-03 (dead branch)
_types.py           8 stmts   0 miss  100%
core.py           137 stmts   0 miss  100%
storage.py         43 stmts   0 miss  100%
__init__.py         3 stmts   0 miss  100%
```

**Target after Phase 5:** All modules 100%. Total coverage: 100%.

Note: removing `list_single_page` reduces `_pagination.py` from 16 to ~10 statements; the 1 uncovered miss disappears with the function.
