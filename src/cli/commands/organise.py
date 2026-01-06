"""Organise command for the Photidy CLI"""

import time
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
    image_files: Optional[list] = None,
) -> None:
    """Organise photos into folders based on their metadata"""
    last_scan = load_last_scan()

    if not source and not image_files and last_scan:
        dir_path = last_scan.get("directory")
        image_files = last_scan.get("image_files")

        if dir_path:
            response = console.input(
                f"\n[cyan]Would you like to organise photos from {dir_path}? (y/n): [/cyan]"
            )
            if response.lower() in ("y", "yes"):
                source = str(dir_path)
            else:
                console.print("\n[bold yellow]Operation cancelled[/bold yellow]\n")
                raise typer.Exit(code=0)

    if not source:
        source = console.input("\n[cyan]Enter source directory: [/cyan]")

    source_path = validate_and_expand_path(source)
    if source_path is None:
        console.print("\n[red]Error: [/red] Invalid source directory\n")
        raise typer.Exit(code=1)
    source = str(source_path)

    if not image_files:
        image_files = scan_cmd(source)
        if not image_files:
            console.print(
                "\n[red]Error: [/red] No photo files found for organisation\n"
            )
            raise typer.Exit(code=1)

    output = output or console.input("\n[cyan]Enter output directory: [/cyan]")
    output_path = validate_and_expand_path(output)
    if output_path is None:
        console.print("\n[red]Error: [/red] Invalid output directory\n")
        raise typer.Exit(code=1)
    output = str(output_path)

    try:
        start_time = time.perf_counter()
        organise_photos(source, output, image_files=image_files)
        end_time = time.perf_counter()

    except InvalidDirectoryError as e:
        console.print(f"\n[red]Directory error: [/red] {e}\n")
        raise typer.Exit(code=1)
    except PhotoOrganisationError as e:
        console.print(f"\n[red]Organisation error: [/red] {e}\n")
        raise typer.Exit(code=1)
    except PhotoMetadataError as e:
        console.print(f"\n[red]Metadata error: [/red] {e}\n")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: [/red] {e}\n")
        raise typer.Exit(code=1)

    console.print(
        f"\n[bold green]Photos organised successfully in {end_time - start_time:.3f}s![/bold green]"
    )
    console.print(f"\n[bold green]Output Directory: [/bold green] {Path(output)}\n")
