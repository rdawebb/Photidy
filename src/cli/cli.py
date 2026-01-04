"""CLI interface for Photidy application"""

import typer

from .commands.organise import organise_cmd
from .commands.scan import scan_cmd
from .commands.undo import undo_cmd

app = typer.Typer(help="Photidy CLI - Photo Organisation Made Easy")


@app.command()
def scan(
    directory: str = typer.Argument(
        ..., help="Directory to scan for photos", metavar="DIRECTORY"
    ),
) -> None:
    """Scan a directory for photos and display the results"""
    scan_cmd(directory)


@app.command()
def organise(
    source: str = typer.Argument(
        None, help="Source directory containing photos", metavar="SOURCE"
    ),
    output: str = typer.Argument(
        None, help="Output directory for organised photos", metavar="DEST"
    ),
) -> None:
    """Organise photos from the source directory to the output directory"""
    organise_cmd(source, output)


@app.command()
def undo() -> None:
    """Undo the last photo organisation operation"""
    undo_cmd()


if __name__ == "__main__":
    app()
