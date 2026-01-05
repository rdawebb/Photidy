"""Undo command for the Photidy CLI"""

import time

import typer
from rich.console import Console

from src.core.organiser import undo_organisation
from src.utils.errors import PhotoOrganisationError

console = Console()


def undo_cmd() -> None:
    """Undo the last photo organisation operation"""
    response = console.input(
        "\n[yellow]Are you sure you want to undo the previous organisation? (y/n): [/yellow]"
    )
    if response.lower() in ("y", "yes"):
        try:
            start_time = time.perf_counter()
            if not undo_organisation():
                console.print(
                    "\n[bold yellow]No undo log found, nothing to undo[/bold yellow]\n"
                )
            else:
                end_time = time.perf_counter()
                console.print(
                    f"\n[bold green]Undo operation completed successfully in {end_time - start_time:.3f}s![/bold green]\n"
                )

        except PhotoOrganisationError as e:
            console.print(f"\n[red]Organisation error: [/red] {e}\n")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(
                f"\n[red]Unexpected error during undo operation: [/red] {e}\n"
            )
            raise typer.Exit(code=1)

        raise typer.Exit(code=0)

    else:
        console.print("\n[bold yellow]Undo operation cancelled.[/bold yellow]\n")
        raise typer.Exit(code=0)
