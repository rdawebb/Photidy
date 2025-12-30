"""Main application window"""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        """Initialise the main window"""
        super().__init__()
        self.setWindowTitle("📷 Photidy")

        # Set up the native app menubar
        menubar = self.menuBar()
        menubar.clear()
        file_menu = menubar.addMenu("&File")
        self.exit_action = QAction("&Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.on_exit)
        file_menu.addAction(self.exit_action)

        self.resize(800, 600)
        self._center_window()

    def _center_window(self):
        """Center the window on screen"""
        screen = self.screen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

    def on_exit(self):
        """Handle the exit menu item"""
        self.close()
