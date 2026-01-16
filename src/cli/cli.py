"""CLI interface for Photidy application"""

from typer_extensions import ExtendedTyper

from .commands.organise import organise_cmd
from .commands.scan import scan_cmd
from .commands.undo import undo_cmd

app = ExtendedTyper(help="Photidy CLI - Photo Organisation Made Easy")


@app.command_with_aliases(aliases=["s", "sc", "find"])
def scan(
    directory: str = app.Argument(
        ..., help="Directory to scan for photos", metavar="DIRECTORY"
    ),
) -> None:
    """Scan a directory for photos and display the results"""
    scan_cmd(directory)


@app.command_with_aliases(aliases=["t", "org", "sort"])
def tidy(
    source: str = app.Argument(
        None, help="Source directory containing photos", metavar="SOURCE"
    ),
    output: str = app.Argument(
        None, help="Output directory for organised photos", metavar="DEST"
    ),
) -> None:
    """Organise photos from the source directory to the output directory"""
    organise_cmd(source, output)


@app.command_with_aliases(aliases=["u", "un", "reset"])
def undo() -> None:
    """Undo the last photo organisation operation"""
    undo_cmd()


if __name__ == "__main__":
    app()
