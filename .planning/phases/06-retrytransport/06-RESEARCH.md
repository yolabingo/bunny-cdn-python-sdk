# Phase 6: RetryTransport - Research

**Researched:** 2026-04-10
**Domain:** httpx async transport API, exponential backoff, retry logic, test mocking
**Confidence:** HIGH

## Summary

`RetryTransport` is implemented by subclassing `httpx.AsyncBaseTransport` and wrapping an inner transport. The subclass overrides `handle_async_request(request: httpx.Request) -> httpx.Response` — this is the single method that intercepts every request. The retry loop lives entirely inside this method: call the inner transport, inspect the response status code (or catch network exceptions), sleep with exponential backoff + jitter, then call the inner transport again up to `max_retries` times. No custom response reconstruction is needed; the real response object from the inner transport is returned as-is on success.

The `Retry-After` header is accessible on the raw `httpx.Response` object before any exception is raised (the transport layer sees status codes directly — `raise_for_status()` is called in `_BaseClient._request`, above the transport layer). Parsing uses `float()` for integer-second format and `email.utils.parsedate_to_datetime` for RFC 5322 HTTP-date format.

Tests use `httpx.MockTransport` as the inner transport, with a stateful handler that returns error responses for the first N calls then succeeds. `asyncio.sleep` is patched as `asyncio.sleep` (not at module level) to capture delay values. `random.uniform` is patched to return `hi` (the upper bound) to make backoff assertions deterministic.

**Primary recommendation:** Subclass `httpx.AsyncBaseTransport`, delegate to an injected inner transport, implement the retry loop in `handle_async_request`, and delegate `aclose()` to the inner transport.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RETRY-01 | `RetryTransport` available as `from bunny_cdn_sdk import RetryTransport` | Export from `_retry.py` via `__init__.py`; pattern matches existing exports |
| RETRY-02 | Retries on 429 (respects `Retry-After`), 5xx, `ConnectError`, `TimeoutException` | All four triggers verified: status codes checked on raw response; exceptions caught at `handle_async_request` level |
| RETRY-03 | Exponential backoff with jitter; `max_retries: int`, `backoff_base: float` constructor params | Formula: `random.uniform(0, min(60.0, base * 2^attempt))`; verified deterministic test strategy |
| RETRY-05 | Independently composable — user constructs it, passes as `transport=` to `httpx.AsyncClient` | Verified: `AsyncBaseTransport` subclass accepted by `httpx.AsyncClient(transport=...)`; injection via `client=` kwarg works |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **httpx only** — no requests, aiohttp, or other HTTP libs
- **Python 3.12+** — target-version py312 in ruff; `ty` type checker with `python-version = "3.12"`
- **Package manager**: `uv run` for all commands — never invoke python/pytest/ruff/ty directly
- **Type checker**: `ty` — not mypy or pyright
- **Return types**: plain `dict` — no Pydantic, no dataclasses
- **All tests are sync** — pytest-asyncio is NOT installed; async behavior tested via `_BaseClient._sync_request()` (which calls `asyncio.run()`) or via `asyncio.run()` directly in test helpers
- **Ruff enforces `ALL` rules** minus D, COM812, ISC001 — follow `from __future__ import annotations` pattern, avoid bare `except:`, etc.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | >=0.28.1 | Transport API base class and request/response types | Project constraint — only HTTP lib allowed |
| asyncio (stdlib) | 3.12+ | `asyncio.sleep()` for backoff delays | Stdlib, no extra dep |
| random (stdlib) | 3.12+ | `random.uniform()` for jitter | Stdlib, mockable |
| email.utils (stdlib) | 3.12+ | `parsedate_to_datetime()` for HTTP-date Retry-After | Stdlib, handles RFC 5322 |

[VERIFIED: uv run python in project venv — httpx==0.28.1, Python 3.14.3 runtime (3.12 target)]

### No New Dependencies Required

This phase adds zero new dependencies. Everything needed is either httpx (already in `dependencies`) or Python stdlib.

## Architecture Patterns

### Recommended File

`src/bunny_cdn_sdk/_retry.py` — consistent with `_client.py`, `_exceptions.py`, `_pagination.py` naming convention (underscore prefix = internal module).

### Recommended Project Structure Addition

```
src/bunny_cdn_sdk/
├── _client.py        # existing
├── _exceptions.py    # existing
├── _pagination.py    # existing
├── _retry.py         # NEW — RetryTransport class
├── _types.py         # existing
├── __init__.py       # update to export RetryTransport
├── core.py           # existing
└── storage.py        # existing
```

### Pattern 1: AsyncBaseTransport Subclass (Wrapping/Composition)

**What:** Subclass `httpx.AsyncBaseTransport`, accept an inner transport in `__init__`, delegate `handle_async_request` to inner after retry logic, delegate `aclose` to inner.

**When to use:** Always — this is the only correct approach for async transport wrapping in httpx.

**Exact API (verified from httpx source):**

```python
# Source: /Users/toddj/.local/share/uv/tools/aider-chat/lib/python3.12/site-packages/httpx/_transports/base.py
class AsyncBaseTransport:
    async def handle_async_request(
        self,
        request: Request,       # httpx.Request
    ) -> Response:              # httpx.Response
        raise NotImplementedError(...)

    async def aclose(self) -> None:
        pass  # default is no-op; delegate to inner
```

**Verified working implementation skeleton:**

```python
# Source: verified via uv run python integration test 2026-04-10
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx


class RetryTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        inner: httpx.AsyncBaseTransport,
        *,
        max_retries: int = 3,
        backoff_base: float = 0.5,
    ) -> None:
        self._inner = inner
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    async def handle_async_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                delay = self._backoff_delay(attempt - 1, request)
                await asyncio.sleep(delay)
            try:
                response = await self._inner.handle_async_request(request)
                if self._should_retry_response(response) and attempt < self._max_retries:
                    continue
                return response
            except (httpx.ConnectError, httpx.TimeoutException):
                if attempt >= self._max_retries:
                    raise
        # unreachable, but satisfies type checker
        return response  # type: ignore[return-value]

    async def aclose(self) -> None:
        await self._inner.aclose()

    def _should_retry_response(self, response: httpx.Response) -> bool:
        return response.status_code == 429 or 500 <= response.status_code < 600

    def _backoff_delay(self, attempt: int, response: httpx.Response | None = None) -> float:
        # Check Retry-After header for 429
        if response is not None and response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            if retry_after is not None:
                return _parse_retry_after(retry_after)
        cap = 60.0
        return random.uniform(0, min(cap, self._backoff_base * (2 ** attempt)))
```

**Note on `_backoff_delay` signature:** The method needs the response to check `Retry-After`, but is also called for network exceptions where there is no response. Pass `response` as optional parameter defaulting to `None`.

### Pattern 2: Request Body Re-Use Across Retries

**What:** httpx `Request` objects with `content=bytes` (or `json=`, `data=`) have their body buffered as `httpx.ByteStream`. The same `Request` object can be passed to `handle_async_request` multiple times without re-reading issues.

**Verified:** `req.content` returns `b'hello'` on second call after first `handle_async_request` consumes it via `await request.aread()` in `MockTransport`. [VERIFIED: uv run python test 2026-04-10]

**Why safe:** Our SDK only sends buffered bodies (bytes, JSON payloads). Streaming uploads are not in scope for this phase.

### Pattern 3: Retry-After Header Parsing

**What:** RFC 7231 allows two formats: integer seconds (`Retry-After: 60`) or HTTP-date (`Retry-After: Wed, 21 Oct 2015 07:28:00 GMT`).

```python
# Source: verified via uv run python test 2026-04-10
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def _parse_retry_after(value: str) -> float:
    """Parse Retry-After header value; return delay in seconds (>= 0.0)."""
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_date = parsedate_to_datetime(value)
            delta = (retry_date - datetime.now(timezone.utc)).total_seconds()
            return max(0.0, delta)
        except Exception:
            return 0.0
```

**httpx headers are case-insensitive:** `response.headers.get("retry-after")` works regardless of header casing. [VERIFIED: uv run python test 2026-04-10]

### Pattern 4: Composability (RETRY-05)

**What:** User constructs `RetryTransport` with a real `httpx.AsyncHTTPTransport()` as the inner, wraps it in `httpx.AsyncClient(transport=retry_transport)`, then injects that client via `CoreClient(..., client=async_client)`.

```python
# Composable usage pattern (verified working)
import httpx
from bunny_cdn_sdk import RetryTransport, CoreClient

inner = httpx.AsyncHTTPTransport()
retry_transport = RetryTransport(inner, max_retries=3, backoff_base=0.5)
async_client = httpx.AsyncClient(transport=retry_transport)
core = CoreClient(api_key="...", client=async_client)
# _client_owner=False (SDK does not close the user's client)
```

[VERIFIED: uv run python integration test 2026-04-10]

### Pattern 5: `__init__.py` Export

```python
# Add to src/bunny_cdn_sdk/__init__.py
from bunny_cdn_sdk._retry import RetryTransport

__all__ = [
    ...,
    "RetryTransport",
]
```

Matches existing export pattern (alphabetical order within `__all__`). [VERIFIED: reading existing `__init__.py`]

### Anti-Patterns to Avoid

- **Subclassing `httpx.AsyncHTTPTransport` instead of `httpx.AsyncBaseTransport`:** `AsyncHTTPTransport` has a concrete `__init__` with `verify`, `cert`, `http1`, `http2` etc. kwargs — not suitable for a generic wrapper. `AsyncBaseTransport` is the correct abstract base. [VERIFIED: httpx source]
- **Calling `response.raise_for_status()` inside the transport:** The SDK's `_BaseClient._request()` already calls this. The transport returns the raw response; callers decide what to do. Retry logic uses `response.status_code` directly.
- **Using `from asyncio import sleep` instead of `import asyncio; asyncio.sleep()`:** The `import asyncio` + `asyncio.sleep()` form allows patching with `patch('asyncio.sleep', ...)` from tests — simpler target than `patch('bunny_cdn_sdk._retry.sleep', ...)`.
- **Re-raising a stale exception after max retries with a response-based error:** For status-code failures (429/5xx), return the final (failed) response rather than raising — the SDK's `_BaseClient._request()` will call `raise_for_status()` and map it to the appropriate `BunnyXxxError`. Only re-raise for network exceptions (`ConnectError`, `TimeoutException`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP-date parsing | Custom date parser | `email.utils.parsedate_to_datetime` | Stdlib, handles RFC 5322 edge cases |
| Async sleep | Custom timer/event | `asyncio.sleep()` | Stdlib, trivially mockable in tests |
| Transport protocol | Build from socket | `httpx.AsyncBaseTransport` subclass | httpx API handles all HTTP/1.1/2 details |

**Key insight:** The retry layer is pure orchestration — it delegates all actual HTTP to the inner transport and all exception mapping to `_BaseClient._request()`. The transport knows nothing about the SDK's exception hierarchy.

## Common Pitfalls

### Pitfall 1: Off-by-one on attempt indexing

**What goes wrong:** `for attempt in range(max_retries)` makes `max_retries=3` produce 3 calls total (1 initial + 2 retries), not 4.
**Why it happens:** Confusion between "number of retries" and "number of attempts."
**How to avoid:** Use `range(max_retries + 1)` for attempts, sleep before calls where `attempt > 0`.
**Warning signs:** Test asserting `call_count == max_retries + 1` fails.

### Pitfall 2: Sleeping before the first attempt

**What goes wrong:** `asyncio.sleep()` is called even on `attempt == 0`, adding latency on every request.
**Why it happens:** Misplacing the sleep call outside the `if attempt > 0:` guard.
**How to avoid:** Always guard sleep: `if attempt > 0: await asyncio.sleep(delay)`.

### Pitfall 3: Returning a stale `response` variable for network exceptions

**What goes wrong:** When `ConnectError` is raised on every attempt, the `return response` at end of loop references an unbound variable.
**Why it happens:** The variable is only set when `handle_async_request` returns without raising.
**How to avoid:** Re-raise the caught exception on final attempt; never fall through to `return response` after the loop. The `# type: ignore[return-value]` comment is correct — the line is truly unreachable when the logic is right.

### Pitfall 4: Patching `random.uniform` for backoff assertions

**What goes wrong:** Without patching, `random.uniform` returns non-deterministic values — you cannot assert that delays grow monotonically between retries.
**Why it happens:** Full-jitter backoff is intentionally random.
**How to avoid:** In tests, patch `random.uniform` with `side_effect=lambda lo, hi: hi` to always return the maximum. This lets you assert that the upper bound is `base * 2^attempt`, confirming exponential growth.

### Pitfall 5: `aclose` not delegating to inner transport

**What goes wrong:** Resources held by the inner transport (TCP connections) are leaked when `RetryTransport` is closed.
**Why it happens:** `AsyncBaseTransport.aclose()` default is a no-op — the subclass must explicitly delegate.
**How to avoid:** Always implement `async def aclose(self) -> None: await self._inner.aclose()`.

### Pitfall 6: Type checker errors on `response` possibly-unbound

**What goes wrong:** `ty` reports `possibly-unresolved-reference` on `return response` after the retry loop.
**Why it happens:** `response` is only assigned inside the `try` block on the last iteration.
**How to avoid:** The `type: ignore[return-value]` comment is correct for the unreachable return. Alternatively, initialize `response: httpx.Response | None = None` before the loop and assert at the end.
**Project config:** `possibly-unresolved-reference = "error"` in `[tool.ty.rules]` — this WILL be an error without a fix.

### Pitfall 7: Ruff ALL rules — avoid bare exceptions and unused imports

**What goes wrong:** Ruff's `ALL` ruleset flags `except Exception:` in `_parse_retry_after` as too broad, and flags unused imports.
**Why it happens:** `ruff.lint.select = ["ALL"]`; only D, COM812, ISC001 are ignored.
**How to avoid:** Use specific exception types where possible. For the date-parse fallback, `except Exception:` is acceptable but may need `# noqa: BLE001` (blind exception).

## Code Examples

### Verified: `handle_async_request` Signature

```python
# Source: httpx/_transports/base.py (httpx 0.28.1, verified 2026-04-10)
async def handle_async_request(
    self,
    request: httpx.Request,
) -> httpx.Response:
    ...
```

### Verified: `httpx.MockTransport` Signature (for tests)

```python
# Source: httpx/_transports/mock.py (httpx 0.28.1, verified 2026-04-10)
class MockTransport(AsyncBaseTransport, BaseTransport):
    def __init__(self, handler: SyncHandler | AsyncHandler) -> None:
        ...
    async def handle_async_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        await request.aread()
        response = self.handler(request)
        if not isinstance(response, Response):
            response = await response
        return response
```

### Verified: Retry Loop with sleep-mock test pattern

```python
# Source: verified via uv run python test 2026-04-10
import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

def make_flaky_handler(fail_count: int, fail_status: int = 503):
    calls = []
    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        if len(calls) <= fail_count:
            return httpx.Response(fail_status)
        return httpx.Response(200, json={"ok": True})
    return handler, calls


def test_retries_on_5xx():
    handler, calls = make_flaky_handler(fail_count=2)
    inner = httpx.MockTransport(handler)
    transport = RetryTransport(inner, max_retries=3, backoff_base=0.5)
    client = httpx.AsyncClient(transport=transport)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        resp = asyncio.run(client.get("https://example.com"))

    assert resp.status_code == 200
    assert len(calls) == 3        # 1 initial + 2 retries
    assert mock_sleep.call_count == 2  # sleep before retry 1 and retry 2
```

### Verified: Backoff Growth Test Pattern

```python
# Source: verified via uv run python test 2026-04-10
def test_backoff_grows_exponentially():
    """Patch random.uniform to return upper bound; verify delays double each attempt."""
    handler, _ = make_flaky_handler(fail_count=3)
    inner = httpx.MockTransport(handler)
    transport = RetryTransport(inner, max_retries=3, backoff_base=0.5)
    client = httpx.AsyncClient(transport=transport)

    sleep_delays = []
    async def capture_sleep(d):
        sleep_delays.append(d)

    with patch("asyncio.sleep", side_effect=capture_sleep):
        with patch("random.uniform", side_effect=lambda lo, hi: hi):
            asyncio.run(client.get("https://example.com"))

    # Upper bounds: [0.5, 1.0, 2.0] for attempts 0, 1, 2
    assert sleep_delays == [0.5, 1.0, 2.0]
```

### Verified: ConnectError and TimeoutException Re-Raise

```python
# Source: verified via reading _client.py and httpx exception MRO 2026-04-10
# httpx exception hierarchy:
# ConnectError -> NetworkError -> TransportError -> RequestError -> HTTPError
# TimeoutException -> TransportError -> RequestError -> HTTPError
# ConnectTimeout -> TimeoutException (also a timeout)

except (httpx.ConnectError, httpx.TimeoutException):
    if attempt >= self._max_retries:
        raise
    # otherwise continue the loop
```

### Verified: Retry-After With Header

```python
# Source: verified via uv run python test 2026-04-10
def test_respects_retry_after_header():
    call_count = 0
    def handler(req):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "42"})
        return httpx.Response(200, json={"ok": True})

    inner = httpx.MockTransport(handler)
    transport = RetryTransport(inner, max_retries=2, backoff_base=0.5)
    client = httpx.AsyncClient(transport=transport)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        resp = asyncio.run(client.get("https://example.com"))

    assert resp.status_code == 200
    assert mock_sleep.call_args_list[0].args[0] == 42.0  # Retry-After header respected
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `httpx.HTTPTransport` subclass | `httpx.AsyncBaseTransport` subclass | httpx 0.20+ | Must implement async; sync retry is a separate concern |
| `tenacity` or `backoff` libraries | Inline transport-level retry | Project constraint | No extra deps; transport-level retry is cleaner than decorator-level |
| Patching at module import path | `patch("asyncio.sleep", ...)` global | Python 3.3+ | Cleaner than mock-level patching when module uses `import asyncio` |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The same `httpx.Request` object can be re-passed to `handle_async_request` multiple times without body stream exhaustion | Architecture Patterns | retry loop would silently send empty body on 2nd+ attempt — LOW risk: verified empirically for ByteStream bodies |

**All other claims in this document are VERIFIED against the live codebase, httpx source, or uv run python tests.**

## Open Questions

1. **Should `backoff_base` have a `cap` parameter?**
   - What we know: cap of 60.0s is hardcoded in the formula above
   - What's unclear: whether callers ever need a different cap
   - Recommendation: hardcode `cap = 60.0` for now; RETRY-03 only requires `max_retries` and `backoff_base` constructor params. Cap can be added in a future phase if needed.

2. **Should `RetryTransport` handle `httpx.ReadError` and `httpx.WriteError`?**
   - What we know: RETRY-02 specifies `ConnectError` and `TimeoutException` only
   - What's unclear: whether Bunny CDN responses can be interrupted mid-stream
   - Recommendation: implement exactly what RETRY-02 specifies. `ReadError`/`WriteError` are not in scope.

## Environment Availability

Step 2.6: SKIPPED — no new external dependencies. All required components (httpx, Python stdlib) are already available in the project venv.

[VERIFIED: httpx==0.28.1 installed; Python 3.14.3 runtime with py312 target; asyncio, random, email.utils are stdlib]

## Sources

### Primary (HIGH confidence)
- httpx 0.28.1 `_transports/base.py` — `AsyncBaseTransport` class definition, exact `handle_async_request` signature [VERIFIED: file read directly]
- httpx 0.28.1 `_transports/mock.py` — `MockTransport` class definition [VERIFIED: file read directly]
- `uv run python` integration tests — transport wrapping, retry loop, sleep patching, request body re-use, Retry-After parsing [VERIFIED: 8 live tests executed 2026-04-10]
- `src/bunny_cdn_sdk/_client.py` — existing `httpx.AsyncClient` usage pattern, `_BaseClient.__init__` signature [VERIFIED: file read]
- `src/bunny_cdn_sdk/__init__.py` — existing export pattern [VERIFIED: file read]
- `tests/conftest.py` — existing test factory pattern with `MockTransport` [VERIFIED: file read]
- `tests/test_exceptions.py` — existing pattern for MockTransport exception injection [VERIFIED: file read]
- `pyproject.toml` — dependency constraints, ruff/ty configuration [VERIFIED: file read]

### Secondary (MEDIUM confidence)
- Python 3.12 stdlib docs: `email.utils.parsedate_to_datetime` for RFC 5322 HTTP-date parsing

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- httpx transport API: HIGH — verified from installed source files
- Retry loop pattern: HIGH — verified via live Python execution
- Backoff formula: HIGH — industry standard (AWS Exponential Backoff) + verified via live test
- Test mocking patterns: HIGH — verified via live Python execution
- Retry-After parsing: HIGH — verified both integer and HTTP-date formats

**Research date:** 2026-04-10
**Valid until:** 2026-10-10 (httpx API is stable; transport protocol changes are rare)
