"""Main GUI entry point"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

from src.ui.main_window import MainWindow


def main():
    app = QApplication([])

    # Set application metadata (used for menus on macOS)
    QCoreApplication.setApplicationName("Photidy")
    QCoreApplication.setApplicationVersion("0.1.0")

    main_window = MainWindow()
    main_window.show()
    app.exec()


if __name__ == "__main__":
    main()
