"""CLI utilities for Photidy"""

import json
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from src.utils.paths import scan_cache

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
    table = Table(
        title="Scan Results",
        title_style="green",
        box=box.ASCII,
        show_header=False,
        width=40,
    )
    table.add_column(justify="left", style="cyan", no_wrap=True)
    table.add_column(justify="right", style="magenta")

    for category, count in summary.items():
        if (
            category == "image_files"
            or (category == "inaccessible_count" and count == 0)
            or (category == "other_count" and count == 0)
        ):
            continue
        c = category.replace("_", " ").replace("count", "").title()
        table.add_row(c, str(count))

    console.print(table)


def save_last_scan(directory: str, image_files: list) -> None:
    """Save the last scan results to a file.

    Args:
        directory (str): The directory that was scanned.
        image_files (list): The list of photo files found in the scan.
    """
    try:
        path_strings = [str(p) for p in image_files]
        with open(scan_cache, "w") as f:
            json.dump({"directory": directory, "image_files": path_strings}, f)
    except Exception as e:
        console.print(f"\n[red]Error saving scan results: [/red] {e}")


def load_last_scan() -> dict:
    """Load the last scan results from a file.

    Returns:
        dict: The last scan results, including the directory and photo files.
    """
    try:
        with open(scan_cache, "r") as f:
            data = json.load(f)
        data["image_files"] = [Path(p) for p in data.get("image_files", [])]
        return data
    except Exception as e:
        console.print(f"\n[red]Error loading scan results: [/red] {e}")
        return {}
