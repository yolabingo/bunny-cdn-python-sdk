"""Machine-readable description of the CLI (``bunnycdn schema``) and the help footer.

Typer vendors Click privately, so commands and params are duck-typed (``Any``).
"""

from __future__ import annotations

from typing import Any, get_args

import typer
import typer.core

SCHEMA_VERSION = 1

_FOOTER_TEXT = (
    "Scripts and AI agents: `bunnycdn schema` prints every command as JSON; "
    "--output-format json|json-file gives JSON output. "
    "NO_COLOR=1 TYPER_USE_RICH=0 give plain text."
)
# Rich renders the markup dim; plain help (TYPER_USE_RICH=0) would print it literally.
FOOTER = f"[dim]{_FOOTER_TEXT}[/dim]" if typer.core.HAS_RICH else _FOOTER_TEXT


def _with_footer(epilog: Any) -> str:
    # Idempotent: add_footer may run more than once on the same app (e.g. in tests).
    if not isinstance(epilog, str) or not epilog or epilog == FOOTER:
        return FOOTER
    return epilog if epilog.endswith(FOOTER) else f"{epilog}\n\n{FOOTER}"


def add_footer(app: typer.Typer) -> None:
    """Append the footer to the help epilog (e.g. examples) of ``app`` and every command."""
    app.info.epilog = _with_footer(app.info.epilog)
    for cmd in app.registered_commands:
        cmd.epilog = _with_footer(cmd.epilog)
    for group in app.registered_groups:
        if group.typer_instance is not None:
            add_footer(group.typer_instance)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    return str(value)


def _type_and_choices(p: Any) -> tuple[str, Any]:
    if hasattr(p, "type"):  # typer < 0.29: Click ParamType
        return p.type.name, getattr(p.type, "choices", None)
    # typer >= 0.29 dropped `.type`; rebuild Click's names so schema_version 1 output is unchanged.
    d = p.type_descriptor
    if d.is_choice:
        return "choice", [getattr(c, "value", c) for c in d.choices or ()]
    if d.is_ranged:
        return f"{d.ranged_type_name} range", None
    # Click reported a list's item type; `multiple` carries the list-ness.
    name = get_args(d.annotation)[0].__name__ if d.is_list else p.bare_type()
    return {"bool": "boolean"}.get(name, name), None


def _param(p: Any) -> dict[str, Any]:
    type_name, choices = _type_and_choices(p)
    return {
        "name": max(p.opts, key=len) if p.param_type_name == "option" else p.name,
        "kind": p.param_type_name,
        "type": type_name,
        "required": p.required,
        "multiple": p.multiple,
        "is_flag": getattr(p, "is_flag", False),
        "default": _jsonable(p.default),
        "envvar": p.envvar,
        "choices": _jsonable(list(choices)) if choices else None,
        "help": getattr(p, "help", None),
    }


def _summary(cmd: Any) -> str:
    return (cmd.help or "").strip().split("\n", 1)[0]


def _params(cmd: Any) -> list[dict[str, Any]]:
    return [_param(p) for p in cmd.params if p.name != "help"]


def _leaves(cmd: Any, path: str) -> list[dict[str, Any]]:
    if not hasattr(cmd, "commands"):  # a command, not a group
        return [{"command": path, "help": _summary(cmd), "params": _params(cmd)}]
    return [
        leaf
        for name, sub in sorted(cmd.commands.items())
        if not sub.hidden
        for leaf in _leaves(sub, f"{path} {name}")
    ]


def build_schema(app: typer.Typer, name: str, version: str) -> dict[str, Any]:
    """Describe ``app``: global options plus one entry per runnable command."""
    root = typer.main.get_command(app)
    return {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "version": version,
        "usage": f"{name} [GLOBAL OPTIONS] COMMAND [ARGS]...",
        "global_options": _params(root),
        "commands": _leaves(root, name),
    }
