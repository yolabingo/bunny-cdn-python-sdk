"""Storage file CLI sub-app."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import typer

from bunny_cdn_sdk.cli._output import err_console, output_result, sdk_errors

storage_app = typer.Typer(no_args_is_help=True, help="Manage Bunny CDN storage files.")
_COLUMNS = ["ObjectName", "Length", "IsDirectory", "LastChanged"]


@storage_app.command("list")
def list_files(
    ctx: typer.Context,
    path: str = typer.Argument("/", help="Storage path to list (default: zone root)"),
) -> None:
    """List files and directories at a storage path."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.storage import StorageClient

    state = cast("State", ctx.obj)
    if not state.zone_name or not state.storage_key:
        err_console.print(
            "Missing storage auth. Use --zone-name/--storage-key "
            "or set BUNNY_STORAGE_ZONE/BUNNY_STORAGE_KEY."
        )
        raise typer.Exit(1)
    with sdk_errors():
        client = StorageClient(state.zone_name, state.storage_key, region=state.region)
        files = client.list(path)
        output_result(files, columns=_COLUMNS, json_mode=state.json_output)


@storage_app.command("upload")
def upload_file(
    ctx: typer.Context,
    local_path: str = typer.Argument(..., help="Local file path to upload"),
    remote_path: str = typer.Argument(..., help="Destination path in storage zone"),
) -> None:
    """Upload a local file to storage."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.storage import StorageClient

    state = cast("State", ctx.obj)
    if not state.zone_name or not state.storage_key:
        err_console.print(
            "Missing storage auth. Use --zone-name/--storage-key "
            "or set BUNNY_STORAGE_ZONE/BUNNY_STORAGE_KEY."
        )
        raise typer.Exit(1)
    with sdk_errors():
        if not Path(local_path).is_file():
            msg = f"Local file not found: {local_path!r}"
            raise ValueError(msg)
        client = StorageClient(state.zone_name, state.storage_key, region=state.region)
        with Path(local_path).open("rb") as fh:
            client.upload(remote_path, fh.read())
        typer.echo(f"Uploaded {local_path!r} -> {remote_path!r}")


@storage_app.command("download")
def download_file(
    ctx: typer.Context,
    remote_path: str = typer.Argument(..., help="Storage path to download"),
    local_path: str = typer.Argument(..., help="Local destination path"),
) -> None:
    """Download a storage file to local filesystem. Overwrites local_path if it exists."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.storage import StorageClient

    state = cast("State", ctx.obj)
    if not state.zone_name or not state.storage_key:
        err_console.print(
            "Missing storage auth. Use --zone-name/--storage-key "
            "or set BUNNY_STORAGE_ZONE/BUNNY_STORAGE_KEY."
        )
        raise typer.Exit(1)
    with sdk_errors():
        client = StorageClient(state.zone_name, state.storage_key, region=state.region)
        data = client.download(remote_path)
        try:
            Path(local_path).write_bytes(data)
        except OSError as exc:
            raise ValueError(str(exc)) from exc
        typer.echo(f"Downloaded {remote_path!r} -> {local_path!r}")


@storage_app.command("delete")
def delete_file(
    ctx: typer.Context,
    remote_path: str = typer.Argument(..., help="Storage path to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a file from storage (prompts for confirmation)."""
    from bunny_cdn_sdk.cli._app import State
    from bunny_cdn_sdk.storage import StorageClient

    state = cast("State", ctx.obj)
    if not state.zone_name or not state.storage_key:
        err_console.print(
            "Missing storage auth. Use --zone-name/--storage-key "
            "or set BUNNY_STORAGE_ZONE/BUNNY_STORAGE_KEY."
        )
        raise typer.Exit(1)
    with sdk_errors():
        if not yes:
            typer.confirm(f"Delete {remote_path!r} from storage zone?", abort=True)
        client = StorageClient(state.zone_name, state.storage_key, region=state.region)
        client.delete(remote_path)
        typer.echo(f"Deleted {remote_path!r}.")
