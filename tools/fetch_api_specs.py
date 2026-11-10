"""Fetch Bunny's published OpenAPI specs into docs/apis/ (gzipped JSON) and report changes.

Specs are discovered from Bunny's docs index, so new APIs appear automatically.
docs/apis/manifest.json records each spec's source URL, content hash and
info.version; a spec file is rewritten only when its content changes.

Usage:
    uv run tools/fetch_api_specs.py           # fetch, update files, print changes
    uv run tools/fetch_api_specs.py --check   # fetch, write nothing, exit 1 if anything changed
"""

import argparse
import gzip
import hashlib
import json
import re
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

INDEX_URL = "https://bunny.net/docs/_llms/api-reference.txt"
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "apis"
MANIFEST = OUT_DIR / "manifest.json"
USER_AGENT = "bunny-cdn-sdk-spec-fetcher"

# Readable file names for known specs; unknown URLs fall back to a slug of the URL.
NAMES = {
    "core-api-public-docs.b-cdn.net/docs/v3/public.json": "core",
    "core-api-public-docs.b-cdn.net/docs/v3/compute.json": "edge-scripting",
    "bunny.net/docs/api-reference/origin-errors/openapi.json": "origin-errors",
    "bunny.net/docs/api-reference/storage/openapi.json": "storage",
    "logging.bunnycdn.com/docs/all/swagger.json": "logging",
    "video.bunnycdn.com/openapi/bunnynet-video-api.public.json": "stream",
    "api.bunny.net/shield/docs/v1/swagger.json": "shield",
    "api-mc.opsbunny.net/docs/public/swagger.json": "magic-containers",
    "core-api-public-docs.b-cdn.net/docs/v3/PartnerPortal.json": "partner",
}

# Published specs missing from the docs index's '## OpenAPI Specs' list.
EXTRA_URLS = ["https://core-api-public-docs.b-cdn.net/docs/v3/PartnerPortal.json"]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def discover_spec_urls(index: str) -> list[str]:
    """Return absolute spec URLs listed under the index's '## OpenAPI Specs' heading."""
    section = index.split("## OpenAPI Specs", 1)
    if len(section) != 2:
        raise SystemExit(
            f"'## OpenAPI Specs' section not found in {INDEX_URL}; index format changed?"
        )
    body = section[1].split("\n## ", 1)[0]
    return sorted({urljoin(INDEX_URL, u) for u in re.findall(r"\]\(([^)\s]+)\)", body)})


def spec_name(url: str) -> str:
    p = urlparse(url)
    key = p.netloc + p.path
    return NAMES.get(key) or re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")


def canonical_hash(spec: object) -> str:
    # Hash a key-sorted form so formatting/key-order churn upstream is not reported as a change.
    blob = json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--check", action="store_true", help="write nothing; exit 1 if any spec changed"
    )
    args = parser.parse_args()

    old = json.loads(MANIFEST.read_text())["specs"] if MANIFEST.exists() else {}
    urls = sorted({*discover_spec_urls(fetch(INDEX_URL).decode()), *EXTRA_URLS})
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    new: dict[str, dict] = {}
    files: dict[str, object] = {}
    errors: list[str] = []
    for url in urls:
        name = spec_name(url)
        try:
            spec = json.loads(fetch(url))
        except Exception as exc:  # keep going; one broken endpoint shouldn't block the rest
            errors.append(f"{name}: {url}: {exc}")
            if name in old:
                new[name] = old[name]  # keep last known-good entry and file
            continue
        digest = canonical_hash(spec)
        prev = old.get(name, {})
        changed = prev.get("sha256") != digest
        new[name] = {
            "url": url,
            "file": f"{name}.json.gz",
            "title": spec.get("info", {}).get("title"),
            "version": spec.get("info", {}).get("version"),
            "spec_format": spec.get("openapi") or spec.get("swagger"),
            "paths": len(spec.get("paths", {})),
            "sha256": digest,
            "updated_at": now if changed else prev.get("updated_at", now),
        }
        if changed or not (OUT_DIR / new[name]["file"]).exists():
            files[name] = spec

    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    changed = sorted(n for n in new.keys() & old.keys() if new[n]["sha256"] != old[n]["sha256"])

    for label, names in (("added", added), ("changed", changed), ("removed", removed)):
        for n in names:
            info = new.get(n) or old[n]
            print(f"{label:8} {n:18} {info.get('version')!s:10}{info['url']}")
    if not (added or changed or removed):
        print(f"no changes ({len(new)} specs)")
    for e in errors:
        print(f"ERROR    {e}", file=sys.stderr)

    if args.check:
        return 1 if (added or changed or removed or errors) else 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, spec in files.items():
        text = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
        # mtime=0 keeps the .gz byte-identical for identical content, so git sees no churn.
        (OUT_DIR / new[name]["file"]).write_bytes(gzip.compress(text.encode(), mtime=0))
    # Drop files no longer referenced (removed specs, or the old uncompressed .json names).
    stale = {e["file"] for e in old.values()} - {e["file"] for e in new.values()}
    for f in stale:
        (OUT_DIR / f).unlink(missing_ok=True)
    if added or changed or removed or stale or not MANIFEST.exists():
        # Rewritten only on change so a no-op run leaves git clean.
        manifest = {
            "source_index": INDEX_URL,
            "updated_at": now,
            "specs": dict(sorted(new.items())),
        }
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
