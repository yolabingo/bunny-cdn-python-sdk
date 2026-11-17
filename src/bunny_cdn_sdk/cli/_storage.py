"""Storage file CLI sub-app."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import typer

from bunny_cdn_sdk.cli._options import examples
from bunny_cdn_sdk.cli._output import output_result, require_storage_auth, sdk_errors

storage_app = typer.Typer(no_args_is_help=True, help="Manage Bunny CDN storage files.")
_COLUMNS = ["ObjectName", "Length", "IsDirectory", "LastChanged"]


@storage_app.command(
    "list",
    epilog=examples(
        "bunnycdn storage list",
        "bunnycdn storage list images/2026/",
    ),
)
def list_files(
    ctx: typer.Context,
    path: str = typer.Argument(
        "/", help="Directory to list, relative to the zone root and ending with / (default: root)"
    ),
) -> None:
    """List files and directories at a storage path.

    Paths are relative to the root of the storage zone
    (BUNNY_STORAGE_ZONE); directory paths end with /.
    """
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.storage import StorageClient

    state = cast("State", ctx.obj)
    require_storage_auth(state)
    with sdk_errors():
        client = StorageClient(state.zone_name, state.storage_key, region=state.region)
        files = client.list(path)
        output_result(files, columns=_COLUMNS, json_mode=state.json_output)


@storage_app.command(
    "upload",
    epilog=examples(
        "bunnycdn storage upload ./logo.png images/logo.png",
        "bunnycdn storage upload ./site.css css/site.css",
    ),
)
def upload_file(
    ctx: typer.Context,
    local_path: str = typer.Argument(..., help="Local file to upload, e.g. ./logo.png"),
    remote_path: str = typer.Argument(
        ..., help="Destination file path relative to the zone root, e.g. images/logo.png"
    ),
) -> None:
    """Upload a local file to storage.

    Replaces any existing file at the destination.
    """
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.storage import StorageClient

    state = cast("State", ctx.obj)
    require_storage_auth(state)
    with sdk_errors():
        if not Path(local_path).is_file():
            msg = f"Local file not found: {local_path!r}"
            raise ValueError(msg)
        client = StorageClient(state.zone_name, state.storage_key, region=state.region)
        with Path(local_path).open("rb") as fh:
            client.upload(remote_path, fh)
        typer.echo(f"Uploaded {local_path!r} -> {remote_path!r}")


@storage_app.command(
    "download",
    epilog=examples(
        "bunnycdn storage download images/logo.png ./logo.png",
    ),
)
def download_file(
    ctx: typer.Context,
    remote_path: str = typer.Argument(
        ..., help="File to download, relative to the zone root, e.g. images/logo.png"
    ),
    local_path: str = typer.Argument(..., help="Local file to write; overwritten if it exists"),
) -> None:
    """Download a storage file to local filesystem. Overwrites local_path if it exists."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.storage import StorageClient

    state = cast("State", ctx.obj)
    require_storage_auth(state)
    with sdk_errors():
        client = StorageClient(state.zone_name, state.storage_key, region=state.region)
        data = client.download(remote_path)
        try:
            Path(local_path).write_bytes(data)
        except OSError as exc:
            raise ValueError(str(exc)) from exc
        typer.echo(f"Downloaded {remote_path!r} -> {local_path!r}")


@storage_app.command(
    "delete",
    epilog=examples(
        "bunnycdn storage delete images/old.png",
        "bunnycdn storage delete images/old.png --yes",
    ),
)
def delete_file(
    ctx: typer.Context,
    remote_path: str = typer.Argument(..., help="File to delete, relative to the zone root"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a file from storage (prompts for confirmation)."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.storage import StorageClient

    state = cast("State", ctx.obj)
    require_storage_auth(state)
    with sdk_errors():
        if not yes:
            typer.confirm(f"Delete {remote_path!r} from storage zone?", abort=True)
        client = StorageClient(state.zone_name, state.storage_key, region=state.region)
        client.delete(remote_path)
        typer.echo(f"Deleted {remote_path!r}.")
