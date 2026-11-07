#!/usr/bin/env bash
# Fetch the latest upstream poethepoet skill (SKILL.md + references/) and report what's there.
# Usage: fetch_upstream.sh [cache_dir]   — prints the local path, upstream version, installed poe version, file list.
set -euo pipefail

REPO="https://github.com/nat-n/poethepoet.git"
SUBDIR="poethepoet/skills/poethepoet"
CACHE="${1:-${TMPDIR:-/tmp}/poethepoet-upstream-skill}"

if [ -d "$CACHE/.git" ]; then
  git -C "$CACHE" fetch -q --depth 1 origin HEAD
  git -C "$CACHE" reset -q --hard FETCH_HEAD
else
  rm -rf "$CACHE"
  git clone -q --depth 1 --filter=blob:none --sparse "$REPO" "$CACHE"
  git -C "$CACHE" sparse-checkout set "$SUBDIR"
fi

DIR="$CACHE/$SUBDIR"
[ -f "$DIR/SKILL.md" ] || { echo "upstream skill not found at $SUBDIR — layout changed?" >&2; exit 1; }

echo "path:      $DIR"
echo "commit:    $(git -C "$CACHE" log -1 --format='%h %cs')"
echo "upstream:  $(cat "$DIR/version.txt" 2>/dev/null || echo unknown)"
echo "installed: $(uv run poe --version 2>/dev/null | awk '{print $NF}' || echo 'not installed')"
echo "files:"
(cd "$DIR" && find . -type f -name '*.md' | sed 's|^\./|  |' | sort)
