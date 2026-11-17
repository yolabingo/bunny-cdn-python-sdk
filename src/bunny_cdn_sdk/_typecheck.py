"""Compare a decoded JSON value against its spec-generated type (internal, debug-only).

Bunny's specs drift from what the API returns. Mismatches are logged at DEBUG (see
``_log``), never raised: the types exist for static checking, not validation.
"""

from __future__ import annotations

import functools
import types
from typing import (
    Any,
    NotRequired,
    Required,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    is_typeddict,
)

from bunny_cdn_sdk._log import debug_enabled, log

_MAX_REPORTED = 20


@functools.cache
def _hints(td: type) -> dict[str, Any]:
    return get_type_hints(td)


def _name(tp: Any) -> str:
    return getattr(tp, "__name__", None) or str(tp)


def mismatches(value: Any, tp: Any, path: str = "$") -> list[str]:  # noqa: C901, PLR0911, PLR0912 — one flat switch over type forms
    """Return one message per place ``value`` doesn't fit ``tp`` (empty when it fits)."""
    while isinstance(tp, TypeAliasType):  # generated `type X = ...` aliases
        tp = tp.__value__
    origin = get_origin(tp)
    if tp is Any:
        return []
    if origin in (Required, NotRequired):
        return mismatches(value, get_args(tp)[0], path)
    if origin in (Union, types.UnionType):
        options = get_args(tp)
        if any(not mismatches(value, opt, path) for opt in options):
            return []
        return [f"{path}: {type(value).__name__} not in {' | '.join(map(_name, options))}"]
    if tp is None or tp is type(None):
        return [] if value is None else [f"{path}: expected null, got {type(value).__name__}"]
    if is_typeddict(tp):
        if not isinstance(value, dict):
            return [f"{path}: expected object {_name(tp)}, got {type(value).__name__}"]
        hints = _hints(tp)
        out = []
        for key, item in value.items():
            if key in hints:
                out += mismatches(item, hints[key], f"{path}.{key}")
            else:
                out.append(f"{path}.{key}: key not in {_name(tp)}")
        return out
    if origin is list:
        if not isinstance(value, list):
            return [f"{path}: expected array, got {type(value).__name__}"]
        (item_tp,) = get_args(tp) or (Any,)
        return [m for i, v in enumerate(value) for m in mismatches(v, item_tp, f"{path}[{i}]")]
    if origin is dict:
        if not isinstance(value, dict):
            return [f"{path}: expected object, got {type(value).__name__}"]
        _, val_tp = get_args(tp) or (str, Any)
        return [m for k, v in value.items() for m in mismatches(v, val_tp, f"{path}.{k}")]
    if tp is float:  # JSON has one number type; 1 is a valid float
        ok = isinstance(value, int | float) and not isinstance(value, bool)
    elif tp is int:
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif isinstance(tp, type):
        ok = isinstance(value, tp)
    else:
        return []  # a construct this checker doesn't model; don't guess
    return [] if ok else [f"{path}: expected {_name(tp)}, got {type(value).__name__}"]


def log_mismatches(value: Any, tp: Any, *, method: str, url: str) -> None:
    """At DEBUG, log how ``value`` differs from ``tp``. Never raises."""
    if not debug_enabled():
        return
    try:
        found = mismatches(value, tp)
    except Exception:  # noqa: BLE001 — a checker bug must never break an API call
        log.debug("response_type_check_skipped", method=method, url=url, exc_info=True)
        return
    if found:
        log.debug(
            "response_type_mismatch",
            method=method,
            url=url,
            spec_type=_name(tp),
            mismatches=found[:_MAX_REPORTED],
            more=max(0, len(found) - _MAX_REPORTED),
        )
