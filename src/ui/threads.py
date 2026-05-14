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
        import time

        results: dict[str, int | list[str]] = {
            "organised": 0,
            "skipped": 0,
            "errors": [],
        }

        # Your actual organisation logic here
        total: int = len(self.file_paths) if self.file_paths else 847
        for i in range(total):
            time.sleep(0.01)
            self.progress.emit(i + 1, total, f"photo_{i}.jpg")
            results["organised"] = i + 1

        self.finished.emit(results)
