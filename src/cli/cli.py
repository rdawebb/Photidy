"""CLI interface for Photidy application"""

import typer

from .commands.scan import scan


app = typer.Typer(help="Photidy CLI - Photo Organisation Made Easy")


@app.command()
def scan_cmd(
    directory: str = typer.Argument(
        ..., help="Directory to scan for photos", metavar="DIRECTORY"
    ),
) -> None:
    """Scan a directory for photos and display the results"""
    scan(directory)


if __name__ == "__main__":
    app()
