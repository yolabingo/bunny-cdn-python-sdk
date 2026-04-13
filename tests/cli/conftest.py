"""Shared fixtures for CLI tests."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """Return a CliRunner for in-process CLI invocation."""
    return CliRunner(env={"NO_COLOR": "1"})
