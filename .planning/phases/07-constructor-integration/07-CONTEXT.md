# Phase 07: Constructor Integration — Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire `max_retries: int = 0` and `backoff_base: float = 0.5` kwargs into `_BaseClient`, `CoreClient`, and `StorageClient` constructors so users get automatic retry behavior without manual `RetryTransport` wiring. `max_retries=0` (default) must preserve exact v1.0 behavior (no `RetryTransport` created, no behavior change).

Also add `client=` to `CoreClient.__init__` (currently missing — injected via `__new__` workaround).

Out of scope: any change to `RetryTransport` itself, new retry triggers, StreamClient, or v2 features.

</domain>

<decisions>
## Implementation Decisions

### client= + max_retries > 0 conflict

**Decision (locked):** Emit `warnings.warn()` when `client=` and `max_retries > 0` are both provided. After warning, ignore `max_retries` — the injected client owns its transport stack. The SDK never modifies an injected client.

Implementation:
```python
import warnings

if client is not None and max_retries > 0:
    warnings.warn(
        "max_retries is ignored when client= is provided. "
        "Configure RetryTransport on your AsyncClient directly.",
        UserWarning,
        stacklevel=2,
    )
```

### CoreClient constructor signature

**Decision (locked):** Phase 7 adds `client=`, `max_retries`, and `backoff_base` to `CoreClient.__init__` together. This eliminates the `__new__` workaround for `client=` injection. All three kwargs pass through to `super().__init__()`.

Final `CoreClient.__init__` signature:
```python
def __init__(
    self,
    api_key: str,
    base_url: str = _BASE_URL,
    *,
    client: httpx.AsyncClient | None = None,
    max_retries: int = 0,
    backoff_base: float = 0.5,
) -> None:
    super().__init__(api_key, client=client, max_retries=max_retries, backoff_base=backoff_base)
    self.base_url = base_url.rstrip("/")
```

### Claude's Discretion

- `_BaseClient.__init__` wires up `RetryTransport` when `max_retries > 0` and `client is None`:
  ```python
  from bunny_cdn_sdk._retry import RetryTransport
  import httpx
  transport = RetryTransport(httpx.AsyncHTTPTransport(), max_retries=max_retries, backoff_base=backoff_base)
  self._client = httpx.AsyncClient(transport=transport)
  self._client_owner = True
  ```
- `max_retries=0` default → no `RetryTransport` created → `httpx.AsyncClient()` with default transport (v1.0 parity)
- `StorageClient.__init__` already accepts `client=`; add `max_retries` and `backoff_base` kwargs and pass through to `super()`
- Keyword-only (`*`) for `client=`, `max_retries`, `backoff_base` on all three classes — prevents positional ambiguity

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing implementation to modify
- `src/bunny_cdn_sdk/_client.py` — `_BaseClient.__init__` — add kwargs, wire RetryTransport
- `src/bunny_cdn_sdk/core.py` — `CoreClient.__init__` — add client=, max_retries, backoff_base
- `src/bunny_cdn_sdk/storage.py` — `StorageClient.__init__` — add max_retries, backoff_base

### RetryTransport (Phase 6 output — read before touching _client.py)
- `src/bunny_cdn_sdk/_retry.py` — RetryTransport constructor signature: `__init__(inner: httpx.AsyncBaseTransport, *, max_retries: int = 3, backoff_base: float = 0.5)`

### Test infrastructure
- `tests/conftest.py` — MockTransport and existing fixtures
- `tests/test_retry.py` — Phase 6 test patterns to follow for new integration tests

### Requirements
- `.planning/REQUIREMENTS.md` — RETRY-04 is the sole requirement for this phase

</canonical_refs>

<specifics>
## Specific References

- `warnings.warn(..., UserWarning, stacklevel=2)` — `stacklevel=2` so the warning points to the caller's constructor call, not the internals of `_BaseClient.__init__`
- `RetryTransport(httpx.AsyncHTTPTransport(), ...)` — inner transport is `httpx.AsyncHTTPTransport()`, not `httpx.AsyncBaseTransport()` (which is abstract)
- All three kwargs (`client=`, `max_retries=`, `backoff_base=`) should be keyword-only (after `*`) to prevent positional argument confusion

</specifics>

<deferred>
## Deferred Ideas

None — all user-raised topics are in scope for Phase 7.

</deferred>

---

*Phase: 07-constructor-integration*
*Context gathered: 2026-04-10 via discuss-phase*
