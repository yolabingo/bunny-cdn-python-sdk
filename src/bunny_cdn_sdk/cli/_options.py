"""Shared CLI option helpers: dates and ranges, ``--set`` help, and help examples."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import typer
import typer.core

WHEN_FORMATS = "YYYY-MM-DD, an ISO timestamp, or relative: now, today, yesterday, 30m, 24h, 7d, 2w"
SET_HELP = (
    "API field as KEY=VALUE (repeatable). Values are read as JSON, so false, 3600 and "
    "'[\"US\"]' keep their types; quote to force a string: Name='\"123\"'"
)

_RELATIVE = re.compile(r"^(\d+)([mhdw])$")
_UNITS = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}


def utcnow() -> datetime:
    """The current time; the one clock CLI date handling reads (tests patch it)."""
    return datetime.now(tz=UTC)


def when(value: str, *, hint: str, now: datetime | None = None) -> datetime:
    """Parse a CLI date/time into an aware UTC datetime (see ``WHEN_FORMATS``)."""
    now = now or utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    text = value.strip().lower()
    fixed = {"now": now, "today": today, "yesterday": today - timedelta(days=1)}
    if text in fixed:
        return fixed[text]
    if m := _RELATIVE.match(text):
        return now - timedelta(**{_UNITS[m[2]]: int(m[1])})
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        msg = f"can't read {value!r} as a date; use {WHEN_FORMATS}"
        raise typer.BadParameter(msg, param_hint=hint) from None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def date_range(from_: str, to: str, *, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Parse ``--from``/``--to`` and check the order."""
    start, end = when(from_, hint="--from", now=now), when(to, hint="--to", now=now)
    if start > end:
        msg = f"--from ({from_}) is after --to ({to})"
        raise typer.BadParameter(msg, param_hint="--from")
    return start, end


def from_option(default: str) -> Any:
    """``--from`` with a default shown in help."""
    return typer.Option(default, "--from", help=f"Start: {WHEN_FORMATS}")


def to_option(default: str) -> Any:
    """``--to`` with a default shown in help."""
    return typer.Option(default, "--to", help=f"End: {WHEN_FORMATS}")


def examples(*lines: str) -> str:
    """A help epilog listing example invocations, one per line in rich and plain help."""
    # Plain help needs \b to stop Click rewrapping the block; rich keeps lines as-is.
    keep = "" if typer.core.HAS_RICH else "\b\n"
    return "Examples:\n\n" + keep + "\n".join(f"  {line}" for line in lines)
