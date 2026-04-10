<!-- GSD:project-start source:PROJECT.md -->
## Project

**bunny-cdn-sdk**

A thin, typed Python SDK wrapping the Bunny CDN REST APIs using `httpx`. Provides two service clients — Core and Storage — with a sync public API backed by async internals for concurrent batch operations. Designed for Python developers who need a clean, dependency-light interface to Bunny CDN without any magic.

**Core Value:** A Python developer can `pip install bunny-cdn-sdk`, instantiate a client with their API key, and call methods that map 1:1 to Bunny CDN endpoints — no surprises, no hidden behavior.

### Constraints

- **Tech stack**: httpx only — no requests, aiohttp, or other HTTP libs
- **Python version**: 3.10+ (union types, match statements if needed, modern asyncio)
- **Package manager**: `uv` — not pip directly
- **Type checker**: `ty` — not mypy or pyright
- **Return types**: plain `dict` from `response.json()` — no Pydantic, no dataclasses
- **Auth**: `AccessKey` header injection per-client — no credential sharing between clients
- **API fidelity**: method signatures match HLD exactly — no deviation without explicit decision
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
