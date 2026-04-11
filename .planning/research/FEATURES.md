# Feature Landscape: Typer CLI for bunny-cdn-sdk

**Domain:** CLI wrapper around a REST SDK (CDN management)
**Researched:** 2026-04-10
**Confidence:** HIGH (based on direct SDK source reading, Typer patterns from training data verified against stable API, pyproject.toml constraints)

---

## Typer Nested-Subcommand Pattern

### How app.add_typer Works

Typer's nested-subcommand model uses one `typer.Typer()` instance per resource group. Each sub-app is registered on the root app via `app.add_typer(sub_app, name="resource-name")`. The root app itself has no commands — only sub-apps.

```python
# src/bunny_cdn_sdk/cli/main.py
import typer
from bunny_cdn_sdk.cli import pull_zone, storage_zone, dns_zone, video_library, storage

app = typer.Typer(help="Bunny CDN management CLI")
app.add_typer(pull_zone.app, name="pull-zone")
app.add_typer(storage_zone.app, name="storage-zone")
app.add_typer(dns_zone.app, name="dns-zone")
app.add_typer(video_library.app, name="video-library")
app.add_typer(storage.app, name="storage")

# Each sub-module exposes its own Typer instance:
# src/bunny_cdn_sdk/cli/pull_zone.py
app = typer.Typer(help="Manage Bunny CDN pull zones")

@app.command("list")
def list_pull_zones(ctx: typer.Context, ...): ...

@app.command("get")
def get_pull_zone(ctx: typer.Context, id: int, ...): ...
```

Invocation: `bunny pull-zone list`, `bunny pull-zone get 12345`, `bunny dns-zone create`.

**Key constraint:** Typer derives command names from function names by replacing underscores with hyphens unless `name=` is given explicitly. Using the `name=` argument on `@app.command()` is safer for multi-word commands.

### Global Options — Callback/Context Approach

Typer provides two approaches for global options: a callback on the root app, or passing options through `typer.Context`. The callback approach is correct for auth:

```python
# Callback on root app (runs before any subcommand)
@app.callback()
def main(
    ctx: typer.Context,
    api_key: str = typer.Option(None, envvar="BUNNY_API_KEY", help="Core API key"),
    storage_key: str = typer.Option(None, envvar="BUNNY_STORAGE_KEY", help="Storage key"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    ctx.ensure_object(dict)
    ctx.obj["api_key"] = api_key
    ctx.obj["storage_key"] = storage_key
    ctx.obj["json_output"] = json_output
```

Sub-commands access the context via `ctx.obj`. This avoids threading global variables and keeps each command testable in isolation.

**Important:** `ctx.ensure_object(dict)` must be called before writing to `ctx.obj`. Typer propagates the context to sub-apps when `invoke_without_command=True` is set or via `@app.callback()`.

**Alternative — per-command options:** Each command declares `api_key` and `json_output` as its own options (no shared context). This is simpler but verbose. Avoid it: 37 commands times 2-3 repeated options is not maintainable.

### Env Var Auth Pattern

```python
api_key: str = typer.Option(
    ...,  # required — no default
    envvar="BUNNY_API_KEY",
    help="Bunny CDN account API key (or set BUNNY_API_KEY env var)",
    show_default=False,
)
```

Using `...` (Ellipsis) as the default makes the option required unless the env var is set. Typer resolves env vars before falling back to the default. If neither is set, Typer exits with a clear error message.

**Storage client specifics:** StorageClient also needs `--zone-name` because its constructor takes `zone_name` + `password` (not just a key). The zone name cannot be inferred from the key alone.

```python
storage_key: str = typer.Option(None, envvar="BUNNY_STORAGE_KEY")
zone_name: str = typer.Option(None, envvar="BUNNY_STORAGE_ZONE")
region: str = typer.Option("falkenstein", envvar="BUNNY_STORAGE_REGION")
```

### --json Flag / Rich Table Output

The pattern is a boolean flag in the context, checked at render time:

```python
def _output(data: dict | list, json_output: bool, table_fn: Callable) -> None:
    if json_output:
        import json
        typer.echo(json.dumps(data, indent=2))
    else:
        table_fn(data)
```

Rich tables are built per resource type. A helper module (`cli/output.py` or `cli/_render.py`) centralizes rendering to avoid duplication across 37 commands. Each resource type gets a dedicated render function. Columns should use a curated subset of fields — not all fields — since Bunny API responses include many internal/noise fields.

**No `--json`/`--table` mutual exclusion needed:** `--json` is a boolean flag. When True, skip Rich. When False (default), use Rich. There is no third option, so Click's `choice` mechanism for mutual exclusion is not needed.

### Pagination in CLI Output

The SDK offers two modes for list operations:
- `list_pull_zones(page, per_page)` — single page, returns `HasMoreItems` envelope
- `iter_pull_zones(per_page)` — auto-paginating iterator, yields all items

**CLI recommendation:** Use the `iter_*` methods for list commands by default (fetch all). Expose `--page` / `--per-page` only on list commands where users explicitly want a single page for scripting (e.g., `--page 2 --per-page 50`). When `--page` is omitted, use the iterator.

This is because CLI users expect `bunny pull-zone list` to show *everything*, while API consumers calling `list_pull_zones()` are expected to handle pagination themselves.

**Edge case:** When `--json` is combined with `iter_*`, collect all items into a list before outputting JSON (not streaming JSON lines). Keep it simple.

### Error Display Pattern

**Recommended:** Rich error panel on stderr, then `raise typer.Exit(code=1)`.

```python
from rich.console import Console
from bunny_cdn_sdk._exceptions import BunnyAPIError, BunnyAuthenticationError

err_console = Console(stderr=True)

try:
    result = client.get_pull_zone(id)
except BunnyAuthenticationError:
    err_console.print("[bold red]Authentication failed.[/bold red] Check --api-key or BUNNY_API_KEY.")
    raise typer.Exit(code=1)
except BunnyNotFoundError:
    err_console.print(f"[bold red]Not found:[/bold red] Pull zone {id} does not exist.")
    raise typer.Exit(code=1)
except BunnyAPIError as e:
    err_console.print(f"[bold red]API error {e.status_code}:[/bold red] {e.message}")
    raise typer.Exit(code=1)
```

Using `Console(stderr=True)` keeps stdout clean for piping. Error messages distinguish between auth errors (actionable: check key), not-found (actionable: check ID), and generic API errors (show status + message).

**Do not use `typer.echo(err=True)`** for Rich-formatted output — it bypasses Rich's markup rendering. Use `Console(stderr=True).print(...)` for styled errors.

---

## Table Stakes Features

Features that must be present for the CLI to feel complete. Missing any of these makes the tool feel broken for primary use cases.

| Feature | Why Expected | Complexity | SDK Method(s) | Command Name(s) |
|---------|--------------|------------|---------------|-----------------|
| List pull zones | Primary operation — users need to enumerate before managing | Low | `list_pull_zones` / `iter_pull_zones` | `bunny pull-zone list` |
| Get pull zone by ID | Inspect a specific zone | Low | `get_pull_zone(id)` | `bunny pull-zone get <id>` |
| List storage zones | Core resource management | Low | `list_storage_zones` / `iter_storage_zones` | `bunny storage-zone list` |
| Get storage zone by ID | Inspect a specific zone | Low | `get_storage_zone(id)` | `bunny storage-zone get <id>` |
| List DNS zones | DNS management starting point | Low | `list_dns_zones` / `iter_dns_zones` | `bunny dns-zone list` |
| Get DNS zone by ID | Inspect a specific zone | Low | `get_dns_zone(id)` | `bunny dns-zone get <id>` |
| List video libraries | Video management starting point | Low | `list_video_libraries` | `bunny video-library list` |
| Get video library by ID | Inspect a specific library | Low | `get_video_library(id)` | `bunny video-library get <id>` |
| Storage list files | Core storage browsing | Low | `StorageClient.list(path)` | `bunny storage list [path]` |
| Storage upload | Core storage write | Medium | `StorageClient.upload(path, data)` | `bunny storage upload <local> <remote>` |
| Storage download | Core storage read | Medium | `StorageClient.download(path)` | `bunny storage download <remote> <local>` |
| Storage delete | Core storage write | Low | `StorageClient.delete(path)` | `bunny storage delete <path>` |
| Auth via env vars | Expected for scripting/CI | Low | N/A (Typer `envvar=` param) | `BUNNY_API_KEY`, `BUNNY_STORAGE_KEY` |
| --json output flag | Expected for scripting / pipe to jq | Low | N/A (output rendering) | `--json` on all commands |
| Exit code 1 on error | Expected for shell scripting | Low | N/A (error handler) | All commands |
| Purge pull zone cache | Most-used operational command | Low | `purge_pull_zone_cache(id)` | `bunny pull-zone purge <id>` |
| Purge URL cache | Site-wide cache invalidation | Low | `purge_url(url)` | `bunny purge <url>` |

## Differentiators

Features that aren't expected but add real value and differentiate the CLI from raw curl.

| Feature | Value Proposition | Complexity | SDK Method(s) | Notes |
|---------|-------------------|------------|---------------|-------|
| Rich table output (default) | Human-readable columns vs raw JSON blob | Medium | N/A (rendering) | Curated columns per resource type (not all fields) |
| Create pull zone | Full CRUD at CLI level | Medium | `create_pull_zone(**kwargs)` | `bunny pull-zone create --name foo --origin-url https://...` — kwargs need explicit flags |
| Delete pull zone with confirmation | Prevent accidental deletion | Low | `delete_pull_zone(id)` | `typer.confirm()` before destructive ops |
| Create/Delete DNS zone | Full DNS management | Medium | `create_dns_zone`, `delete_dns_zone` | `bunny dns-zone create --domain example.com` |
| Add/Update/Delete DNS record | Full DNS record CRUD | Medium | `add_dns_record`, `update_dns_record`, `delete_dns_record` | Multi-arg command: `bunny dns-zone record add <zone-id> --type A --name www --value 1.2.3.4` |
| Create/Delete storage zone | Full storage zone lifecycle | Medium | `create_storage_zone`, `delete_storage_zone` | |
| Create/Delete video library | Full video library lifecycle | Low | `create_video_library`, `delete_video_library` | |
| Get CDN statistics | Operational dashboarding | Low | `get_statistics(**kwargs)` | `bunny stats [--pull-zone-id N] [--from YYYY-MM-DD] [--to YYYY-MM-DD]` |
| List countries/regions | Discovery commands | Low | `list_countries`, `list_regions` | Rarely used but rounds out the CLI |
| Get billing | Account health check | Low | `get_billing` | `bunny billing` |
| Add/Remove custom hostname | Pull zone hostname management | Low | `add_custom_hostname`, `remove_custom_hostname` | `bunny pull-zone hostname add <id> <hostname>` |
| Add/Remove blocked IP | Pull zone security | Low | `add_blocked_ip`, `remove_blocked_ip` | `bunny pull-zone block-ip add <id> <ip>` |
| Update pull zone | Settings management | Medium | `update_pull_zone(id, **kwargs)` | kwargs as explicit flags — significant flag surface |
| --page / --per-page flags on list | Power user pagination | Low | `list_*` single-page methods | Use when user wants slice not all |

## Anti-Features

Features to explicitly NOT build in v2.0.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Interactive prompts for create/update fields | 37 methods times N fields = unmaintainable; CLI is not a wizard | Require fields as explicit flags; fail with clear error if missing required field |
| `--output yaml` mode | Adds PyYAML dependency; YAML is not a standard for API output; jq is the standard pipe target | `--json` + jq covers all structured output needs |
| Shell autocompletion scripts | Requires Typer's `typer.completion` module and per-shell setup; complexity not worth the payoff in v2.0 | Defer to v3.0 if requested |
| Configuration file (bunny.toml) | Env vars + CLI flags are sufficient; config file adds a third auth/config source that creates confusion | Env vars are the standard for CI/CD; document them clearly |
| Progress bars for upload | Rich has a progress bar; httpx sync upload doesn't expose progress callbacks; would require streaming hooks | v3.0 candidate when StorageClient gets streaming support |
| Concurrent batch operations via CLI | `get_pull_zones([id1, id2, ...])` is a power-user SDK feature; CLI is for one-at-a-time ops | Document SDK directly for batch use cases |
| `bunny watch` or polling commands | Bunny CDN has no webhook support in the Core API; polling is flaky and eats rate limits | Not in scope |
| JSON Schema validation of create/update inputs | Bunny's API schema is undocumented / changes frequently; the SDK already passes through kwargs | Let the API return 400 with its own error message |
| `--dry-run` mode | Bunny has no dry-run endpoint; faking it in the CLI would be misleading | Document that there is no preview mode |
| Update storage zone CLI command | `update_storage_zone` has many optional kwargs; modeling as CLI flags is complex and rarely needed for storage | Defer to SDK-direct use for this operation |
| Recursive upload/download | Requires local directory traversal + parallel requests; significant complexity vs. value | Defer to v3.0 or a separate tool built on top of this CLI |

## Feature Dependencies

```
BUNNY_API_KEY env var || --api-key flag
  → all CoreClient commands (pull-zone, storage-zone, dns-zone, video-library, purge, stats, billing)

BUNNY_STORAGE_KEY env var || --storage-key flag
BUNNY_STORAGE_ZONE env var || --zone-name flag
  → all StorageClient commands (storage list, upload, download, delete)

Rich installed (optional dep in [cli] extra)
  → default table output (all commands)
  → error panels (all commands)

Typer installed (optional dep in [cli] extra)
  → CLI entry point (all commands)

CoreClient.iter_pull_zones() → bunny pull-zone list (no --page)
CoreClient.list_pull_zones() → bunny pull-zone list --page N --per-page N
```

## Resource Group to Sub-App Mapping

| Sub-App | Command Prefix | SDK Client | Auth Required |
|---------|---------------|------------|---------------|
| `pull_zone.py` | `bunny pull-zone` | `CoreClient` | `BUNNY_API_KEY` |
| `storage_zone.py` | `bunny storage-zone` | `CoreClient` | `BUNNY_API_KEY` |
| `dns_zone.py` | `bunny dns-zone` | `CoreClient` | `BUNNY_API_KEY` |
| `video_library.py` | `bunny video-library` | `CoreClient` | `BUNNY_API_KEY` |
| `storage.py` | `bunny storage` | `StorageClient` | `BUNNY_STORAGE_KEY` + zone name |
| `utils.py` (root) | `bunny purge`, `bunny stats`, `bunny billing` | `CoreClient` | `BUNNY_API_KEY` |

## MVP Recommendation

Prioritize for first phase:

1. Auth context (`--api-key`/`BUNNY_API_KEY`, `--storage-key`/`BUNNY_STORAGE_KEY`, `--json`)
2. `bunny pull-zone list` — proves the whole pattern (sub-app, context, Rich table, `--json` flag)
3. `bunny pull-zone get <id>` — proves single-resource display
4. `bunny pull-zone purge <id>` — proves a write command with no body
5. `bunny storage list [path]` — proves StorageClient wiring and second auth mode
6. `bunny storage upload <local> <remote>` — proves file I/O at CLI boundary
7. `bunny storage download <remote> <local>` — symmetric with upload
8. `bunny purge <url>` — proves a root-level (non-sub-app) command

Remaining CRUD commands follow the same pattern once the above is working. DNS record sub-sub-commands (`bunny dns-zone record add`) are the only structurally different case (a second level of nesting) and should be implemented after the flat pattern is proven.

Defer:
- `bunny dns-zone record *` — nested sub-sub-commands; add after first DNS zone commands ship
- `bunny stats`, `bunny billing` — useful but not table stakes for CLI proving
- `bunny pull-zone hostname *`, `bunny pull-zone block-ip *` — niche; defer to later phase
- `update_*` commands for all resources — flag surface is large; defer to avoid scope creep

## Complexity Notes

| Category | Complexity Driver | Notes |
|----------|-------------------|-------|
| Package setup (`[cli]` optional extra) | Low | pyproject.toml `[project.optional-dependencies]` + `[project.scripts]` — standard uv pattern |
| Root callback + context propagation | Medium | `typer.Context`, `ctx.ensure_object(dict)`, `ctx.obj` — error-prone if context not passed correctly to sub-apps |
| Rich table rendering per resource | Medium | 5-6 resource types x curated columns = significant render code surface, but all mechanical |
| StorageClient constructor mismatch | Medium | StorageClient takes `zone_name` + `password` + `region`, not a single key — CLI must expose all three (or use env vars); zone_name is not derivable from password |
| DNS record nested commands | Medium | `bunny dns-zone record add/update/delete` requires a second `app.add_typer` level; the pattern works but adds structural complexity |
| `update_*` commands with **kwargs | High | Bunny's update endpoints accept many optional fields (pull zone has ~30 config fields); modeling as CLI flags requires either explicit enumeration (tedious) or `--set KEY=VALUE` style (ugly). Defer or limit to most-used fields. |
| `create_pull_zone(**kwargs)` flags | High | Same as update — many optional fields; start with `--name` and `--origin-url` (the required fields) and skip optionals in v2.0 |
| Error handling consistency | Medium | Must catch all `BunnySDKError` subtypes (8 classes) and emit consistent `Console(stderr=True)` output across all 37+ commands — centralize in a decorator or context manager |
| Testing CLI commands | Medium | Use `typer.testing.CliRunner` (included with Typer); mock SDK clients with `unittest.mock.patch`; no new test framework needed |

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Typer `app.add_typer` pattern | HIGH | Stable Typer API since 0.4; confirmed from training data; this is the documented primary pattern |
| `typer.Option(envvar=...)` | HIGH | Standard Typer feature; confirmed from training data |
| Context propagation via `@app.callback()` | HIGH | Standard Typer idiom; widely used |
| Rich `Console(stderr=True)` | HIGH | Rich is already installed in project venv (confirmed); this is the canonical Rich pattern |
| SDK method inventory | HIGH | Read directly from `core.py` (37 methods) and `storage.py` (4 methods) |
| StorageClient auth complexity | HIGH | Read directly from `storage.py` — zone_name + password + region are three separate constructor args |
| `[project.optional-dependencies]` pattern for `[cli]` extra | HIGH | Standard Python packaging; confirmed in pyproject.toml structure |
| DNS record nested sub-commands complexity | MEDIUM | Typer supports it; complexity is real but underdocumented for 3-level nesting |
| `update_*` flag surface problem | MEDIUM | Identified from SDK source; solution options (explicit flags vs KEY=VALUE) have tradeoffs not fully researched |
