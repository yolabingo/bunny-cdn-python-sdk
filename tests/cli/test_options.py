"""Tests for shared CLI option helpers (dates, help examples)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime

import pytest
import typer

from bunny_cdn_sdk.cli import app
from bunny_cdn_sdk.cli._options import date_range, when

NOW = datetime(2026, 11, 17, 15, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("now", "2026-11-17T15:30:00+00:00"),
        ("Today", "2026-11-17T00:00:00+00:00"),
        ("yesterday", "2026-11-16T00:00:00+00:00"),
        ("30m", "2026-11-17T15:00:00+00:00"),
        ("24h", "2026-11-16T15:30:00+00:00"),
        ("7d", "2026-11-10T15:30:00+00:00"),
        ("2w", "2026-11-03T15:30:00+00:00"),
        ("2026-01-31", "2026-01-31T00:00:00+00:00"),  # naive = UTC
        ("2026-01-31T12:00Z", "2026-01-31T12:00:00+00:00"),
        ("2026-01-31T12:00+02:00", "2026-01-31T10:00:00+00:00"),  # converted to UTC
    ],
)
def test_when_formats(value: str, expected: str) -> None:
    assert when(value, hint="--from", now=NOW).isoformat() == expected


@pytest.mark.parametrize("value", ["", "7 days", "-1d", "31/01/2026", "1y"])
def test_when_rejects_unknown(value: str) -> None:
    with pytest.raises(typer.BadParameter, match="can't read"):
        when(value, hint="--from", now=NOW)


def test_date_range_order() -> None:
    assert date_range("7d", "now", now=NOW) == (when("7d", hint="", now=NOW), NOW)
    with pytest.raises(typer.BadParameter, match="is after"):
        date_range("today", "yesterday", now=NOW)


def _example_lines(output: str) -> list[str]:
    plain = re.sub(r"\x1b\[[0-9;]*m", "", output)
    return [line.strip(" │") for line in plain.splitlines()]


def test_examples_and_footer_in_rich_help(runner) -> None:
    result = runner.invoke(app, ["stats", "--help"])
    assert result.exit_code == 0
    lines = _example_lines(result.output)
    assert "Examples:" in lines
    assert "bunnycdn stats --from 30d --sort-by BandwidthUsed" in lines  # one per line
    assert "bunnycdn schema" in result.output  # footer kept after the examples


def test_examples_stay_one_per_line_in_plain_help() -> None:
    # Subprocess because Typer reads TYPER_USE_RICH at import time.
    env = {**os.environ, "NO_COLOR": "1", "TYPER_USE_RICH": "0"}
    code = "from bunny_cdn_sdk.cli import app; app()"
    out = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code, "stats", "--help"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    ).stdout
    lines = _example_lines(out)
    assert "bunnycdn stats --from 30d --sort-by BandwidthUsed" in lines
    assert "bunnycdn schema" in out


def test_every_set_and_date_command_has_examples(runner) -> None:
    # --set KEY=VALUE and date inputs have formats that need showing, not just describing.
    schema = json.loads(runner.invoke(app, ["schema"]).output)
    missing = []
    for cmd in schema["commands"]:
        names = {p["name"] for p in cmd["params"]}
        if names & {"--set", "--from"}:
            args = cmd["command"].split()[1:]
            if "Examples:" not in runner.invoke(app, [*args, "--help"]).output:
                missing.append(cmd["command"])
    assert missing == []
