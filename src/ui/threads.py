"""Background threads for scanning and organising photos"""

from pathlib import Path

from PySide6.QtCore import QThread, Signal


class ScannerThread(QThread):
    """Background thread for scanning directories"""

    progress = Signal(int, str)  # count, filename
    finished = Signal(dict)  # results

    def __init__(self, directory: str):
        super().__init__()
        self.directory: str = directory

    def run(self):
        """Run the scanning process in a background thread"""
        from src.core.organiser import scan_directory

        def progress_callback(count, filename):
            self.progress.emit(count, filename)

        results: dict = scan_directory(
            source_dir=self.directory, progress_callback=progress_callback
        )

        self.finished.emit(results)


class OrganiserThread(QThread):
    """Background thread for organising photos"""

    progress = Signal(int, int, str)  # current, total, current_file
    finished = Signal(dict)  # results

    def __init__(self, file_paths, output_dir, options):
        super().__init__()
        self.file_paths: list[Path] = file_paths
        self.output_dir: Path = output_dir
        self.options: dict = options

    def run(self):
        # Simulate organising - replace with actual implementation
        from src.core.organiser import organise_photos

        source_dir = self.options.get("source_dir", "")
        output_dir = str(self.output_dir)
        total = len(self.file_paths)

        def progress_callback(current: int, filename: str):
            self.progress.emit(current, total, filename)

        results = organise_photos(
            source_dir=source_dir,
            dest_dir=output_dir,
            image_files=self.file_paths,
            progress_callback=progress_callback,
        )
        results["output_dir"] = output_dir
        self.finished.emit(results)
