# Requirements — v2.0 Typer CLI

**Milestone:** v2.0 — Typer CLI
**Status:** Active
**Last updated:** 2026-04-10

---

## v2.0 Requirements

### CLI — Package & Scaffold

- [ ] **CLI-01**: CLI is installable as optional extra via `pip install bunny-cdn-sdk[cli]`
- [ ] **CLI-02**: `bunnycdn` entry point is registered and resolves after `[cli]` install
- [ ] **CLI-03**: Importing SDK core (`import bunny_cdn_sdk`) does not import Typer or Rich
- [ ] **CLI-04**: Running `bunnycdn` without `[cli]` deps installed exits with a clear "install bunny-cdn-sdk[cli]" message

### AUTH — Authentication & Global Options

- [ ] **AUTH-01**: Core commands accept `--api-key` flag; fallback to `BUNNY_API_KEY` env var
- [ ] **AUTH-02**: Storage commands accept `--zone-name` / `BUNNY_STORAGE_ZONE`, `--storage-key` / `BUNNY_STORAGE_KEY`, and `--region` / `BUNNY_STORAGE_REGION` (default: `falkenstein`)
- [ ] **AUTH-03**: `--json` flag is available on all commands and produces raw JSON on stdout
- [ ] **AUTH-04**: Missing required auth (no flag and no env var) exits with a clear actionable error message

### OUT — Output Layer

- [ ] **OUT-01**: All list commands render a Rich table with curated columns by default
- [ ] **OUT-02**: All get commands render a Rich table (single-row or key-value) by default
- [ ] **OUT-03**: `--json` flag on any command outputs raw JSON (list commands collect all items before printing)
- [ ] **OUT-04**: All error messages are printed to stderr via `Console(stderr=True)`, not stdout
- [ ] **OUT-05**: All commands exit with code 0 on success and code 1 on any SDK or auth error
- [ ] **OUT-06**: JSON serialization uses `default=str` fallback to prevent crashes on non-serializable values

### PZ — Pull Zone Commands

- [ ] **PZ-01**: `bunnycdn pull-zone list` lists all pull zones (auto-paginated via `iter_pull_zones`)
- [ ] **PZ-02**: `bunnycdn pull-zone get <id>` displays a single pull zone by ID
- [ ] **PZ-03**: `bunnycdn pull-zone create --name <name> --origin-url <url>` creates a pull zone
- [ ] **PZ-04**: `bunnycdn pull-zone delete <id>` deletes a pull zone with confirmation prompt
- [ ] **PZ-05**: `bunnycdn pull-zone purge <id>` purges the cache for a pull zone
- [ ] **PZ-06**: `bunnycdn pull-zone update <id> --set KEY=VALUE` updates one or more pull zone fields

### SZ — Storage Zone Commands

- [ ] **SZ-01**: `bunnycdn storage-zone list` lists all storage zones
- [ ] **SZ-02**: `bunnycdn storage-zone get <id>` displays a single storage zone by ID
- [ ] **SZ-03**: `bunnycdn storage-zone create --name <name>` creates a storage zone
- [ ] **SZ-04**: `bunnycdn storage-zone delete <id>` deletes a storage zone with confirmation prompt
- [ ] **SZ-05**: `bunnycdn storage-zone update <id> --set KEY=VALUE` updates storage zone fields

### DZ — DNS Zone Commands

- [ ] **DZ-01**: `bunnycdn dns-zone list` lists all DNS zones
- [ ] **DZ-02**: `bunnycdn dns-zone get <id>` displays a single DNS zone by ID
- [ ] **DZ-03**: `bunnycdn dns-zone create --domain <domain>` creates a DNS zone
- [ ] **DZ-04**: `bunnycdn dns-zone delete <id>` deletes a DNS zone with confirmation prompt
- [ ] **DZ-05**: `bunnycdn dns-zone record add <zone-id> --type <type> --name <name> --value <value>` adds a DNS record
- [ ] **DZ-06**: `bunnycdn dns-zone record update <zone-id> <record-id> --set KEY=VALUE` updates a DNS record
- [ ] **DZ-07**: `bunnycdn dns-zone record delete <zone-id> <record-id>` deletes a DNS record with confirmation

### VL — Video Library Commands

- [ ] **VL-01**: `bunnycdn video-library list` lists all video libraries
- [ ] **VL-02**: `bunnycdn video-library get <id>` displays a single video library by ID
- [ ] **VL-03**: `bunnycdn video-library create --name <name>` creates a video library
- [ ] **VL-04**: `bunnycdn video-library delete <id>` deletes a video library with confirmation prompt
- [ ] **VL-05**: `bunnycdn video-library update <id> --set KEY=VALUE` updates video library fields

### ST — Storage File Commands

- [ ] **ST-01**: `bunnycdn storage list [path]` lists files/directories at a storage path
- [ ] **ST-02**: `bunnycdn storage upload <local-path> <remote-path>` uploads a local file to storage
- [ ] **ST-03**: `bunnycdn storage download <remote-path> <local-path>` downloads a storage file locally
- [ ] **ST-04**: `bunnycdn storage delete <remote-path>` deletes a file from storage with confirmation prompt

### UTIL — Utility Commands

- [ ] **UTIL-01**: `bunnycdn purge <url>` purges a specific URL from CDN cache
- [ ] **UTIL-02**: `bunnycdn stats [--pull-zone-id <id>] [--from <date>] [--to <date>]` displays CDN statistics
- [ ] **UTIL-03**: `bunnycdn billing` displays account billing summary

### TEST — CLI Test Suite

- [ ] **TEST-01**: All commands have CliRunner-based tests that mock at the SDK client boundary (not HTTP)
- [ ] **TEST-02**: Tests verify both Rich table output path (exit 0) and error path (exit 1, stderr message)
- [ ] **TEST-03**: Tests verify `--json` flag produces parseable JSON output

---

## Future Requirements

| Feature | Reason deferred |
|---------|-----------------|
| Shell autocomplete | Complexity not worth payoff in v2.0 |
| `bunny pull-zone hostname add/remove` | Niche; add after core CRUD proven |
| `bunny pull-zone block-ip add/remove` | Niche; add after core CRUD proven |
| Recursive storage upload/download | Significant complexity; v3.0 candidate |
| Progress bars for upload | httpx sync doesn't expose upload progress callbacks |
| Config file (`bunnycdn.toml`) | Env vars sufficient; config adds a third auth source |
| `--page`/`--per-page` flags | Most CLI users want all items; add if requested |

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Interactive prompts for create/update fields | Unmaintainable at 37+ methods with N fields each |
| `--output yaml` | Adds PyYAML dep; JSON + jq is the standard |
| Polling / watch commands | Bunny has no webhook support in Core API |
| `--dry-run` mode | Bunny has no dry-run endpoint |
| Concurrent batch operations via CLI | SDK-direct use case, not CLI |
| `StreamClient` / Stream API | Deferred to v3.0 |

---

## Traceability

*(Populated by roadmapper)*
