"""Tests for the debug-only response type checker."""

from __future__ import annotations

import importlib
import logging
from typing import TypedDict, get_type_hints, is_typeddict

import pytest

from bunny_cdn_sdk import _typecheck
from bunny_cdn_sdk._typecheck import log_mismatches, mismatches


class Node(TypedDict, total=False):
    Name: str
    Size: float
    Count: int | None
    Children: list[Node]
    Tags: dict[str, int]


def test_fitting_value_has_no_mismatches() -> None:
    value = {"Name": "a", "Size": 1, "Count": None, "Children": [{"Name": "b"}], "Tags": {"x": 1}}
    assert mismatches(value, Node) == []


def test_reports_wrong_types_unknown_keys_and_paths() -> None:
    value = {"Name": 1, "Count": True, "Children": [{"Size": "big"}], "Tags": {"x": "y"}, "New": 0}
    assert mismatches(value, Node) == [
        "$.Name: expected str, got int",
        "$.Count: bool not in int | NoneType",
        "$.Children[0].Size: expected float, got str",
        "$.Tags.x: expected int, got str",
        "$.New: key not in Node",
    ]


type Nodes = list[Node]


def test_unwraps_type_aliases() -> None:
    assert mismatches([{"Name": 1}], Nodes) == ["$[0].Name: expected str, got int"]


def test_container_shape_mismatches() -> None:
    assert mismatches([], Node) == ["$: expected object Node, got list"]
    assert mismatches({}, list[int]) == ["$: expected array, got dict"]
    assert mismatches(1, None) == ["$: expected null, got int"]


def test_logs_only_at_debug(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="bunny_cdn_sdk"):
        log_mismatches({"Name": 1}, Node, method="GET", url="/x")
    assert caplog.records == []
    with caplog.at_level(logging.DEBUG, logger="bunny_cdn_sdk"):
        log_mismatches({"Name": 1}, Node, method="GET", url="/x")
        log_mismatches({"Name": "ok"}, Node, method="GET", url="/y")
    assert len(caplog.records) == 1
    assert "event='response_type_mismatch' method='GET' url='/x' spec_type='Node'" in caplog.text


def test_checker_bug_never_raises(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_: object) -> list[str]:
        raise RuntimeError

    monkeypatch.setattr(_typecheck, "mismatches", boom)
    with caplog.at_level(logging.DEBUG, logger="bunny_cdn_sdk"):
        log_mismatches({}, Node, method="GET", url="/x")
    assert "response_type_check_skipped" in caplog.text


@pytest.mark.parametrize("api", ["core", "shield", "logging", "storage", "partner"])
def test_every_generated_operation_type_resolves(api: str) -> None:
    # log_mismatches swallows errors, so an unresolvable generated type would only
    # ever show up as "type check skipped" — catch it here instead.
    module = importlib.import_module(f"bunny_cdn_sdk.models.{api}")
    names = {n for pair in module.OPERATIONS.values() for n in pair if n}
    for name in names:
        tp = getattr(module, name)
        mismatches({}, tp)
        mismatches([], tp)
        mismatches({"x": [1, None, {"y": "z"}]}, tp)


@pytest.mark.parametrize("api", ["core", "shield", "logging", "storage", "partner"])
def test_every_generated_typeddict_resolves(api: str) -> None:
    module = importlib.import_module(f"bunny_cdn_sdk.models.{api}")
    tds = [v for v in vars(module).values() if is_typeddict(v)]
    assert tds
    for td in tds:
        get_type_hints(td)
