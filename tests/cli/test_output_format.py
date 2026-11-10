"""--output-format human|json|json-file."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from bunny_cdn_sdk.cli import app

_OVERVIEW = {"CustomerUserId": "u1", "Email": "a@b.c"}


def _get(runner, *fmt: str, env: dict | None = None):
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        M.return_value.get_customer_overview.return_value = _OVERVIEW
        return runner.invoke(
            app, [*fmt, "--api-key", "k", "partner", "customer", "get", "secret-id"], env=env
        )


def test_json_file_writes_temp_file_and_prints_path(runner) -> None:
    result = _get(runner, "--output-format", "json-file")
    assert result.exit_code == 0, result.output
    path = Path(result.stdout.strip())
    try:
        assert path.name.startswith("bunnycdn-partner-customer-get-")
        assert path.suffix == ".json"
        assert "secret-id" not in path.name  # argument values stay out of the name
        assert json.loads(path.read_text()) == _OVERVIEW
    finally:
        path.unlink()


def test_json_file_names_are_unique(runner) -> None:
    paths = [Path(_get(runner, "--output-format", "json-file").stdout.strip()) for _ in range(2)]
    try:
        assert paths[0] != paths[1]
    finally:
        for p in paths:
            p.unlink()


@pytest.mark.parametrize("fmt", ["json", "JSON"])
def test_json_to_stdout_case_insensitive(runner, fmt) -> None:
    result = _get(runner, "--output-format", fmt)
    assert json.loads(result.stdout) == _OVERVIEW


def test_output_format_from_env(runner) -> None:
    result = _get(runner, env={"BUNNY_OUTPUT_FORMAT": "json"})
    assert json.loads(result.stdout) == _OVERVIEW


def test_invalid_output_format_is_usage_error(runner) -> None:
    result = runner.invoke(app, ["--output-format", "xml", "schema"])
    assert result.exit_code == 2
