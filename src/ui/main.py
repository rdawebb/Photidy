"""Main GUI entry point"""

import os
import sys
from pathlib import Path

# Attempt to set the QT_QPA_PLATFORM_PLUGIN_PATH environment variable
_pyside_lib_path = Path(__file__).resolve().parent.parent.parent / ".venv" / "lib"
if _pyside_lib_path.exists():
    # Find the PySide6 site-packages
    site_packages_dirs = list(_pyside_lib_path.glob("python*/site-packages"))
    if site_packages_dirs:
        pyside_path = site_packages_dirs[0] / "PySide6" / "Qt" / "plugins"
        if pyside_path.exists():
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(pyside_path)

if "QT_QPA_PLATFORM_PLUGIN_PATH" not in os.environ:
    try:
        from PySide6 import QtCore

        base = QtCore.__file__
        if base:
            qt_path = Path(base).parent / "Qt" / "plugins"
            if (qt_path / "platforms").exists():
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(qt_path)
    except Exception as e:
        print(f"Warning: Could not detect Qt plugin path: {e}")


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
