"""Scan command for Photidy CLI"""

import typer
from rich.console import Console

from ..utils import display_scan_results, validate_and_expand_path
from src.core.organiser import scan_directory
from src.utils.errors import InvalidDirectoryError

console = Console()


def scan(directory: str) -> None:
    """Scan a directory for photos and display the results

    Args:
        directory (str): The directory to scan for photos.
    """
    try:
        console.print(f"\n[cyan]Scanning: [/cyan] {directory}\n")

        path = validate_and_expand_path(directory)
        scan_results = scan_directory(str(path))

        display_scan_results(scan_results)

        console.print("\n[bold green]Scan complete![/bold green]\n")

    except InvalidDirectoryError as e:
        console.print(f"[red]Error: [/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error: [/red] {e}")
        raise typer.Exit(code=1)
