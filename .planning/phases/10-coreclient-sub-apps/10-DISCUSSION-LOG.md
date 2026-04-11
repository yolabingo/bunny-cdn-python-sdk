# Phase 10: CoreClient Sub-Apps — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 10-coreclient-sub-apps
**Areas discussed:** Delete confirmation, purge placement, iter vs list methods, column curation, update diff format, purge output

---

## Delete Confirmation

| Option | Description | Selected |
|--------|-------------|----------|
| Prompt only, no bypass | Just `typer.confirm()`, no skip flag | |
| --yes/-y flag | Allows scripting/CI to skip confirmation | ✓ |
| You decide | Claude picks simpler approach | |

**User's choice:** `--yes/-y` flag  
**Notes:** Confirmation prompt must include both resource name AND ID (e.g. "Delete pull zone 12345 (my-pull-zone)?")

---

## Purge Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level command | `bunnycdn purge <url>` on root app | ✓ |
| Under a util sub-app | `bunnycdn util purge <url>` | |
| You decide | Claude keeps top-level | |

**User's choice:** Top-level  
**Notes:** Stats/billing in Phase 12 can also be top-level or get their own sub-app then

---

## Iter vs List Methods

| Option | Description | Selected |
|--------|-------------|----------|
| Iterator methods | `iter_*` auto-paginate, collect all items | ✓ |
| Non-iterator list_* | Manual pagination loop required | |
| You decide | Claude uses iterators | |

**User's choice:** Iterator methods (`iter_pull_zones`, `iter_storage_zones`, `iter_dns_zones`, `iter_video_libraries`)

---

## Column Curation — Pull Zone

| Option | Description | Selected |
|--------|-------------|----------|
| Id, Name, OriginUrl, Enabled | 4 key fields | |
| Id, Name, OriginUrl, Enabled, CnameDomain | Adds CDN domain | |
| You decide | Claude picks useful fields | |

**User's choice:** Free text — `Name, OriginUrl, Enabled, Id` (Name first, ID last)  
**Notes:** General rule established: Name first when resource has a Name; ID always last; list commands sort alphabetically by Name

---

## Column Curation — Storage Zone, DNS Zone, Video Library

| Option | Description | Selected |
|--------|-------------|----------|
| SZ: Name, Region, Id \| DZ: Domain, RecordsCount, Id \| VL: Name, VideoCount, Id | Minimal, scannable | ✓ |
| SZ: Name, Region, StorageUsed, Id \| DZ: Domain, Nameserver1, RecordsCount, Id \| VL: Name, VideoCount, PullZoneId, Id | More fields | |
| You decide | Claude picks with Name-first + ID-last | |

**User's choice:** Minimal set (recommended)

---

## DNS Record Output (add/update)

| Option | Description | Selected |
|--------|-------------|----------|
| Table: Name, Type, Value, Id | Single-row table, consistent with get | ✓ |
| Success message only | "Record added (id=123)" | |
| You decide | Claude uses table | |

**User's choice:** Table with columns `["Name", "Type", "Value", "Id"]`

---

## Create Command Output

| Option | Description | Selected |
|--------|-------------|----------|
| Same columns as list view | Reuses list columns, no extra code path | ✓ |
| All fields in key-value table | Full response shown | |
| You decide | Claude reuses list-view columns | |

**User's choice:** Same columns as list view (recommended)

---

## Update Command Output

| Option | Description | Selected |
|--------|-------------|----------|
| Highlight changes if possible | Show diff with visual indicator | ✓ |
| Show updated state only | Single PATCH, no extra GET | |

**Follow-up — fetch before update:**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, fetch before + show diff | 2 API calls, before/after comparison | ✓ |
| No, just show updated state | Single call, no diff | |

**Follow-up — diff format:**

| Option | Description | Selected |
|--------|-------------|----------|
| Field \| Before \| After table (changed rows only) | Compact diff | |
| Standard list-view with changed cells annotated | Full row with old → new | |
| You decide | User specified: red + italic via Rich | ✓ |

**User's choice:** Claude decides format; use Rich colors (red + italic) to highlight changed fields  
**Notes:** User clarified: "use rich colors to highlight changed fields in red, also italics if possible"

---

## Purge Output

| Option | Description | Selected |
|--------|-------------|----------|
| Plain message | "Purged: <url>" | ✓ |
| Table with URL and status | Single-row table | |
| You decide | Claude uses plain message | |

**User's choice:** Plain message (recommended)
