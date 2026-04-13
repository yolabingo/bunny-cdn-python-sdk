"""Shared fixtures for CLI tests."""

from __future__ import annotations

import os

# Force-disable Rich color output before any Rich/typer imports.
# Rich caches terminal detection at import time; setting these here
# ensures plain text output in CliRunner regardless of CI environment
# (GitHub Actions sets FORCE_COLOR=1 which would otherwise override NO_COLOR).
os.environ["NO_COLOR"] = "1"
os.environ["FORCE_COLOR"] = "0"

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """Return a CliRunner for in-process CLI invocation."""
    return CliRunner()
