"""Organise command for the Photidy CLI"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from src.core.organiser import organise_photos
from src.utils.errors import (
    InvalidDirectoryError,
    PhotoMetadataError,
    PhotoOrganisationError,
)

from ..utils import load_last_scan, validate_and_expand_path
from .scan import scan_cmd

console = Console()


def organise_cmd(
    source: Optional[str] = None,
    output: Optional[str] = None,
    photo_files: Optional[list] = None,
) -> None:
    """Organise photos into folders based on their metadata"""
    last_scan = load_last_scan()

    if last_scan and not photo_files and not source:
        dir_path = last_scan.get("directory")
        photo_files = last_scan.get("photo_files")

        response = console.input(
            f"[cyan]Would you like to organise photos from {dir_path}? (y/n): [/cyan]"
        )
        if response.lower() in ("y", "yes"):
            source = validate_and_expand_path(dir_path)
        else:
            console.print("\n[bold yellow]Operation cancelled.[/bold yellow]")
            raise typer.Exit(code=0)

    if not photo_files:
        if not source:
            console.print(
                "\n[red]Error: [/red] No source directory provided for organisation"
            )
            raise typer.Exit(code=1)

        photo_files = scan_cmd(source)
        if not photo_files:
            console.print("\n[red]Error: [/red] No photo files found for organisation.")
            raise typer.Exit(code=1)

    try:
        output = output or console.input("\n[cyan]Enter output directory: [/cyan]")
        output = validate_and_expand_path(output)
        organise_photos(source, output, photo_files=photo_files)
        console.print("\n[bold green]Photos organised successfully![/bold green]")
        console.print(f"\n[bold green]Output Directory: [/bold green] {Path(output)}")

    except InvalidDirectoryError as e:
        console.print(f"\n[red]Directory error: [/red] {e}")
        raise typer.Exit(code=1)
    except PhotoOrganisationError as e:
        console.print(f"\n[red]Organisation error: [/red] {e}")
        raise typer.Exit(code=1)
    except PhotoMetadataError as e:
        console.print(f"\n[red]Metadata error: [/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: [/red] {e}")
        raise typer.Exit(code=1)
