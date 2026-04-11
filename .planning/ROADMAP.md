# Roadmap: bunny-cdn-sdk

## Milestones

- **[v1.0](milestones/v1.0-ROADMAP.md)** *(archived 2026-04-10)* — CoreClient (37 methods), StorageClient (4 ops, 10 regions), httpx-based infrastructure, 58-test MockTransport suite (96% coverage)

---

## v2.0 — Next Milestone

*(Requirements to be defined via `/gsd-new-milestone`)*

Candidates:
- `StreamClient` — Stream API (Videos, Collections, pagination)
- Public surface smoke tests (`from bunny_cdn_sdk import ...`)
- Context manager / `list_single_page` tech debt from v1.0
- Retry / backoff via custom httpx transport
- File upload progress callbacks
