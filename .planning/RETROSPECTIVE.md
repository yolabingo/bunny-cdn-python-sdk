# Retrospective

## Milestone: v1.1 — Reliability & Coverage

**Shipped:** 2026-04-10
**Phases:** 3 | **Plans:** 6 | **Tasks:** 13 | **Commits:** 33

### What Was Built

- Coverage gaps from v1.0 closed: `BunnyAPIError.__str__` tested, `list_single_page` removed, context manager lifecycle paths covered, public surface smoke test added
- `RetryTransport` — composable httpx transport with 429/5xx/network retry, exponential backoff + jitter, Retry-After header parsing
- Constructor retry kwargs (`max_retries`, `backoff_base`) wired into all three client classes; `max_retries=0` default preserves exact v1.0 behavior
- 15 integration tests + 22 retry tests; 98 total; 99% coverage

### What Worked

- **Plan → execute → UAT** pipeline moved fast — all 3 phases executed the same day
- **Self-contained phase summaries** with explicit commit hashes made review easy; no hunting for what changed
- **Plan-time deviation detection** caught the `httpx.AsyncClient.transport` vs `._transport` discrepancy before it became a bug in production code
- **MockTransport injection pattern** (established in v1.0) made retry integration tests straightforward — no live network needed
- **`max_retries=0` default decision** was the right call; backward compat tests confirmed it immediately

### What Was Inefficient

- **VERIFICATION.md files not created** — the workflow ran plan → execute → UAT without a per-phase `/gsd-verify-work` step; SUMMARY self-checks substituted but leave a formal gap
- **Plan code quality** — ruff lint failures in plan-provided code required fixes during execution (7 ruff errors in 06-01, 9+ in 06-02 test code); plans should be pre-validated against the project's ruff ruleset before execution
- **`_client.py` 100% target missed** — Phase 05-02 plan promised 100% coverage on `_client.py` but only 93% achieved; the 4 remaining lines (bare except, 5xx branch) were not in scope for lifecycle tests but the plan didn't flag this
- **MILESTONES.md one-liner extraction failure** — gsd-tools CLI only extracted 1 of 6 accomplishments (others extracted as "One-liner:" placeholder); needed manual fix

### Patterns Established

- **`asyncio.run()` in sync tests** — use `asyncio.run(coroutine())` inside sync test functions to test async code without an async test framework; avoids pytest-asyncio dependency
- **`# noqa: S311` for jitter** — `random.uniform` for jitter is not a cryptographic operation; suppress S311 with inline comment
- **`# pragma: no cover` on unreachable sentinel** — post-loop `return` after `max_retries` exhaustion is unreachable by design; pragma is correct, not a coverage hack
- **`[tool.ruff.lint.per-file-ignores]` for tests/**` — add once to `pyproject.toml` to suppress ANN, ARG, S101, SLF001, PLR2004 for all test files; consistent with pre-existing test conventions

### Key Lessons

1. **Pre-validate plan code against project linter** — if the plan provides exact code, run `ruff check` on it before the plan is committed; saves a deviation cycle during execution
2. **State the metric separately from the functional goal** — QUAL-02 mixed "cover the aclose path" (functional) with "_client.py to 100%" (metric); when the metric isn't achievable in phase scope, the goal reads as failed even if the function is covered. Keep them separate.
3. **Include `RetryTransport` in public surface test upfront** — Phase 06 added `RetryTransport` to `__init__.__all__` but Phase 05's smoke test wasn't updated; minor but worth catching at plan time

### Cost Observations

- Sessions: 1 day, multiple consecutive `/gsd-next` calls
- All execution via `sonnet` model
- No context overflows or checkpoint stops

---

## Cross-Milestone Trends

| Metric | v1.0 | v1.1 |
|--------|------|------|
| Phases | 4 | 3 |
| Plans | 8 | 6 |
| Test count | 58 | 98 |
| Coverage | 96% | 99% |
| Days to ship | 1 | 1 |
| Lint issues introduced | 0 | 0 |
| Deviations auto-fixed | ~3 | ~5 |
