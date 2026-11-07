## Project

**bunny-cdn-sdk**

A thin, typed Python SDK wrapping the Bunny CDN REST APIs using `httpx2`. Provides four service clients — Core, Storage, Shield, Logging — with a sync public API and thread-pooled concurrent batch operations. Designed for Python developers who need a clean, dependency-light interface to Bunny CDN without any magic.

**Core Value:** A Python developer can `pip install bunny-cdn-sdk`, instantiate a client with their API key, and call methods that map 1:1 to Bunny CDN endpoints — no surprises, no hidden behavior.

### Constraints

- **Tech stack**: httpx2 only — no httpx, requests, aiohttp, or other HTTP libs
- **Python version**: 3.12+
- **Package manager**: `uv` — not pip directly; always run commands as `uv run <cmd>` (never invoke python, pytest, ruff, ty directly)
- **Type checker**: `ty` — not mypy or pyright
- **Return types**: plain `dict` from `response.json()` — no Pydantic, no dataclasses
- **Auth**: `AccessKey` header injection per-client — no credential sharing between clients
- **API fidelity**: method signatures match the design doc ([docs/DESIGN.md](docs/DESIGN.md)) exactly — no deviation without explicit decision
