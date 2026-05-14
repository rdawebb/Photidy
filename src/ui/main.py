"""Main GUI entry point"""

import sys


def main():
    """Main entry point for the GUI application"""
    from PySide6.QtWidgets import QApplication

    from src import __version__
    from src.ui.main_window import MainWindow

    app = QApplication([])

    # Set application metadata
    app.setApplicationName("Photidy")
    app.setApplicationVersion(__version__)

    main_window = MainWindow()
    main_window.show()

    main_window.center_window()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
