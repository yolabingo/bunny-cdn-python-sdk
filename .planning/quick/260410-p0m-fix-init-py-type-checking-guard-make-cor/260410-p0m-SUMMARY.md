---
quick_id: 260410-p0m
slug: fix-init-py-type-checking-guard-make-cor
description: "fix __init__.py TYPE_CHECKING guard — make CoreClient/StorageClient direct runtime imports"
date: "2026-04-10"
status: completed
files_modified:
  - src/bunny_cdn_sdk/__init__.py
requirements_closed:
  - INFRA-10
---

# Quick Task 260410-p0m: Fix TYPE_CHECKING Guard in __init__.py

**One-liner:** Removed `if TYPE_CHECKING:` guard; CoreClient and StorageClient are now direct runtime imports, closing the INFRA-10 blocker identified in the v1.0 milestone audit.

## What Was Done

`src/bunny_cdn_sdk/__init__.py` — removed 4 lines, added 2:

- Removed `from typing import TYPE_CHECKING`
- Removed `if TYPE_CHECKING:` block
- Added direct `from bunny_cdn_sdk.core import CoreClient`
- Added direct `from bunny_cdn_sdk.storage import StorageClient`

## Why

The `TYPE_CHECKING` guard was placed in Phase 2 (plan 02-03) as a forward-reference placeholder because CoreClient and StorageClient did not exist yet. Phase 3 implemented the modules but never removed the guard. At runtime `TYPE_CHECKING` is `False`, so both clients were absent from the package namespace — `from bunny_cdn_sdk import CoreClient` raised `ImportError`.

## Verification

```
$ python -c "from bunny_cdn_sdk import CoreClient, StorageClient, BunnyAPIError"
OK: <class 'bunny_cdn_sdk.core.CoreClient'> <class 'bunny_cdn_sdk.storage.StorageClient'> ...

$ uv run ruff check src/bunny_cdn_sdk/__init__.py
All checks passed!

$ uv run pytest --tb=short -q
58 passed in 0.13s   (96% total coverage)
```

`__init__.py` coverage: 4 stmts, 0 miss, 100%.
