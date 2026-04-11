---
phase: 08
slug: cli-scaffold
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-11
---

# Phase 08 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI flag → State | User-supplied `--api-key` value enters via argv; stored in State dataclass | API key (credential) |
| Env var → State | `BUNNY_API_KEY`, `BUNNY_STORAGE_KEY`, `BUNNY_STORAGE_ZONE`, `BUNNY_STORAGE_REGION` read from environment | API key, storage password |
| State → SDK client | `api_key` passed to `CoreClient`; `storage_key` passed to `StorageClient` | API key, storage password |
| Test code → production code | Tests import CLI modules; no external boundaries crossed | None (mocked only) |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-08-01 | Information Disclosure | `--api-key` CLI flag | accept | Env var `BUNNY_API_KEY` documented as preferred method in `typer.Option(help=...)` and visible in `--help` output. Flag value in shell history cannot be mitigated at CLI layer. **Verified:** `envvar="BUNNY_API_KEY"` present in `_app.py:29` with help text "Prefer BUNNY_API_KEY env var." | closed |
| T-08-02 | Elevation of Privilege | `State.api_key` empty-string default | mitigate | Per-command `if not state.api_key:` guard deferred to Phase 10 by design. Phase 08 scaffold wires `State` only; no client is constructed. **Verified:** `State.api_key = field(default="")` in `_app.py:17`; no client instantiation in Phase 08 code. | closed |
| T-08-03 | Information Disclosure | `sdk_errors()` exception messages | accept | Exception messages (`exc.message`) passed to stderr. User is authenticated account holder; no PII involved in CDN management. | closed |
| T-08-04 | Spoofing | ImportError guard message | accept | Guard message cannot be forged meaningfully. **Verified:** `__init__.py` raises `ImportError` unconditionally with install instructions. | closed |
| T-08-05 | Denial of Service | `BunnyTimeoutError` / `BunnyRateLimitError` | mitigate | `sdk_errors()` catches both and exits cleanly with `Exit(1)` and human-readable message. **Verified:** `BunnyRateLimitError` caught at `_output.py:41`, `BunnyTimeoutError` at `_output.py:50`, `BunnySDKError` catch-all at `_output.py:56`. | closed |
| T-08-06 | Information Disclosure | Test fixtures with real API keys | accept | Tests use `unittest.mock.MagicMock()` for response objects; no real credentials in test code. **Verified:** `BUNNY_API_KEY` appears only in help-text assertion (`test_app.py:54`), not as a real key. | closed |
| T-08-07 | Tampering | `CliRunner env=` overrides | accept | CliRunner env injection is the intended test mechanism; risk bounded to test execution only. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-08-01 | T-08-01 | `--api-key` flag value appears in shell history and `ps aux`. Mitigation not possible at CLI layer. Preferred path (env var) documented in `--help`. | GSD orchestrator | 2026-04-11 |
| AR-08-02 | T-08-03 | SDK exception messages may include internal API error details. User is authenticated CDN account holder; no PII exposure. | GSD orchestrator | 2026-04-11 |
| AR-08-03 | T-08-04 | ImportError guard install message cannot be meaningfully forged. | GSD orchestrator | 2026-04-11 |
| AR-08-04 | T-08-06 | Tests use only mocked responses; no credential exposure. | GSD orchestrator | 2026-04-11 |
| AR-08-05 | T-08-07 | CliRunner env injection is test-only; no production impact. | GSD orchestrator | 2026-04-11 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-11 | 7 | 7 | 0 | GSD orchestrator (code verification) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-11
