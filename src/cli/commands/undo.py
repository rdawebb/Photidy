"""Undo command for the Photidy CLI"""

import typer
from rich.console import Console

from src.core.organiser import undo_organisation
from src.utils.errors import PhotoOrganisationError

console = Console()


def undo_cmd() -> None:
    """Undo the last photo organisation operation"""
    response = console.input(
        "[yellow]Are you sure you want to undo the last operation? (y/n): [/yellow]"
    )
    if response.lower() in ("y", "yes"):
        try:
            if not undo_organisation():
                console.print(
                    "\nNo undo log found, nothing to undo",
                    style="bold yellow",
                )
            else:
                console.print(
                    "\nUndo operation completed successfully!", style="bold green"
                )

        except PhotoOrganisationError as e:
            console.print(f"[red]Organisation error: [/red] {e}")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"\n[red]Unexpected error during undo operation: [/red] {e}")
            raise typer.Exit(code=1)

        raise typer.Exit(code=0)

    else:
        console.print("\nUndo operation cancelled.", style="bold yellow")
        raise typer.Exit(code=0)
