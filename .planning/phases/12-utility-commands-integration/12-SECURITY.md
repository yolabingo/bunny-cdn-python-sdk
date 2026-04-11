---
phase: 12
slug: utility-commands-integration
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-11
---

# Phase 12 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI args → SDK calls | `--from`/`--to` date strings from user passed to API as query params | User-controlled strings; no secrets |
| API response → CLI display | Statistics and billing dicts from Bunny CDN rendered into table/JSON output | Authenticated user data only |
| Test mocks → CLI layer | Tests mock at CoreClient boundary; real HTTP never called | Internal test infrastructure |
| README content → user system | Documentation only; no executable content | Public API surface only |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-12-01 | Spoofing | api_key CLI flag | accept | API key is user-supplied and consumed by Bunny CDN's own auth — no spoofing surface within this SDK | closed |
| T-12-02 | Information Disclosure | --json output to stdout | accept | User intentionally requests raw JSON; stdout is under user control; no secrets in statistics/billing responses beyond what the authenticated user already has access to | closed |
| T-12-03 | Tampering | --from/--to date params | mitigate | Date strings passed as-is to API query params (`_app.py:153-154`); no `eval`/`exec`/parsing in SDK; Bunny CDN validates format server-side — confirmed in code | closed |
| T-12-04 | Denial of Service | concurrent gather over many zones | accept | Number of zones is bounded by user's account; no unbounded fan-out from untrusted input; same pattern as `get_pull_zones()` already in SDK | closed |
| T-12-05 | Elevation of Privilege | api_key env var | accept | `BUNNY_API_KEY` is a read-only env var at the process level; standard pattern established by Phases 08-11 | closed |
| T-12-06 | Tampering | test mock patch paths | accept | Mock paths are internal test infrastructure; incorrect paths cause test failures (caught immediately), not security issues | closed |
| T-12-07 | Information Disclosure | README CLI section | accept | README documents public API surface only; no secrets, tokens, or internal URLs in documentation examples | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-12-01 | T-12-01 | API key auth is delegated to Bunny CDN; SDK has no auth surface to protect | orchestrator | 2026-04-11 |
| AR-12-02 | T-12-02 | --json is an intentional user-facing feature; output scope is limited to authenticated user's own data | orchestrator | 2026-04-11 |
| AR-12-04 | T-12-04 | Zone fan-out is account-bounded; no untrusted input controls concurrency count | orchestrator | 2026-04-11 |
| AR-12-05 | T-12-05 | Env var credential pattern is established SDK convention; no escalation surface | orchestrator | 2026-04-11 |
| AR-12-06 | T-12-06 | Test infrastructure only; failures are caught immediately as test errors | orchestrator | 2026-04-11 |
| AR-12-07 | T-12-07 | README is static documentation; no executable content or sensitive data | orchestrator | 2026-04-11 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-11 | 7 | 7 | 0 | orchestrator (threats_open: 0 fast-path) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-11
