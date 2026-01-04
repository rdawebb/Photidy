"""Main GUI entry point"""

import sys

from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


def main():
    app = QApplication([])

    app.setStyle("Fusion")

    # Set application metadata
    app.setApplicationName("Photidy")
    app.setApplicationVersion("0.1.0")

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
