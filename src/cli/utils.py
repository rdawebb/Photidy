"""CLI utilities for Photidy"""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def validate_and_expand_path(path_str: str) -> Path:
    """Validate and expand a directory path

    Args:
        path_str (str): The path string to validate and expand.

    Returns:
        Path: The validated and expanded Path object.

    Raises:
        typer.BadParameter: If the path is invalid or not a directory.
    """
    try:
        path = Path(path_str).expanduser().resolve()
        return path

    except Exception as e:
        raise typer.BadParameter(f"Invalid path: {e}")


def display_scan_results(summary: dict) -> None:
    """Display a summary of the scan results.

    Args:
        summary (dict): The summary dictionary containing scan results.
    """
    table = Table(title="Scan Results", title_style="green")
    table.add_column("Category", justify="left", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="magenta")

    for category, count in summary.items():
        if category == "photo_files":
            continue
        c = category.replace("_", " ").replace("count", "").title()
        table.add_row(c, str(count))

    console.print(table)
