"""Tests for `bunnycdn schema` and the help footer."""

from __future__ import annotations

import json

import pytest

from bunny_cdn_sdk.cli import app
from bunny_cdn_sdk.cli._schema import SCHEMA_VERSION


def _schema(runner) -> dict:
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def test_schema_shape(runner) -> None:
    data = _schema(runner)
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["name"] == "bunnycdn"
    envvars = {o["envvar"] for o in data["global_options"]}
    assert {"BUNNY_API_KEY", "BUNNY_PARTNER_API_KEY"} <= envvars
    commands = {c["command"]: c for c in data["commands"]}
    assert "bunnycdn partner customer product enable" in commands
    assert "bunnycdn schema" in commands
    order = next(
        p for p in commands["bunnycdn partner customer audit"]["params"] if p["name"] == "--order"
    )
    assert order["choices"] == ["Ascending", "Descending"]


def test_every_schema_command_has_working_help(runner) -> None:
    # Guards the schema against listing commands that don't exist.
    for cmd in _schema(runner)["commands"]:
        args = cmd["command"].split()[1:]
        result = runner.invoke(app, [*args, "--help"])
        assert result.exit_code == 0, (cmd["command"], result.output)


@pytest.mark.parametrize("args", [[], ["partner"], ["partner", "customer", "list"]])
def test_help_footer_everywhere(runner, args) -> None:
    result = runner.invoke(app, [*args, "--help"])
    assert "bunnycdn schema" in result.output
    assert "TYPER_USE_RICH=0" in result.output
