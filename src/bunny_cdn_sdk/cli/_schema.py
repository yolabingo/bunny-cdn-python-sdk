"""Machine-readable description of the CLI (``bunnycdn schema``) and the help footer.

Typer vendors Click privately, so commands and params are duck-typed (``Any``).
"""

from __future__ import annotations

from typing import Any

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


def add_footer(app: typer.Typer) -> None:
    """Set the footer as the help epilog of ``app`` and every sub-group and command."""
    app.info.epilog = FOOTER
    for cmd in app.registered_commands:
        cmd.epilog = FOOTER
    for group in app.registered_groups:
        if group.typer_instance is not None:
            add_footer(group.typer_instance)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    return str(value)


def _param(p: Any) -> dict[str, Any]:
    choices = getattr(p.type, "choices", None)
    return {
        "name": max(p.opts, key=len) if p.param_type_name == "option" else p.name,
        "kind": p.param_type_name,
        "type": p.type.name,
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
