"""Scan command for Photidy CLI"""

import time

import typer
from rich.console import Console

from src.core.organiser import scan_directory
from src.utils.errors import InvalidDirectoryError, PhotoOrganisationError

from ..utils import display_scan_results, save_last_scan, validate_and_expand_path

console = Console()


def scan_cmd(directory: str) -> None:
    """Scan a directory for photos, display the results, and save to a cache file.

    Args:
        directory (str): The directory to scan for photos.
    """
    try:
        console.print(f"\n[bold cyan]Scanning: [/bold cyan] {directory}\n")

        path = validate_and_expand_path(directory)

        start_time = time.perf_counter()
        scan_results = scan_directory(str(path))
        end_time = time.perf_counter()

        display_scan_results(scan_results)

        photo_files = scan_results["photo_files"]
        photo_count = scan_results["photos_count"]

        if photo_count == 0:
            console.print(
                "\n[bold yellow]Scan complete - no photos found[/bold yellow]\n"
            )
            save_last_scan(directory, [])
        else:
            console.print(
                f"\n[bold green]Scan complete - {photo_count} photos found in {end_time - start_time:.3f}s![/bold green]\n"
            )

        save_last_scan(directory, photo_files)

    except InvalidDirectoryError as e:
        console.print(f"\n[red]Directory error: [/red] {e}")
        raise typer.Exit(code=1)
    except PhotoOrganisationError as e:
        console.print(f"\n[red]Organisation error: [/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: [/red] {e}")
        raise typer.Exit(code=1)
