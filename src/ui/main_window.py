"""Main application window"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QPixmap
from PySide6.QtWidgets import QMainWindow, QDialog, QVBoxLayout, QLabel, QPushButton

from src import __version__


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        """Initialise the main window"""
        super().__init__()
        self.setWindowTitle("📷 Photidy")

        # Set up the native app menubar
        menubar = self.menuBar()
        menubar.clear()

        # File menu
        file_menu = menubar.addMenu("&File")
        self.exit_action = QAction("&Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.on_exit)
        file_menu.addAction(self.exit_action)

        # Preferences/Settings
        self.prefs_action = QAction("&Settings", self)
        self.prefs_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.prefs_action.setShortcut("Ctrl+,")
        self.prefs_action.triggered.connect(self.on_preferences)
        file_menu.addAction(self.prefs_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        self.about_action = QAction("&About", self)
        self.about_action.setMenuRole(QAction.MenuRole.AboutRole)
        self.about_action.triggered.connect(self.on_about)
        help_menu.addAction(self.about_action)

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

    def on_preferences(self):
        """Handle the preferences menu item"""
        pass

    def on_about(self):
        """Handle the about menu item"""
        about = QDialog(self)
        layout = QVBoxLayout(about)

        # Icon
        icon_label = QLabel()
        pixmap = QPixmap("src/ui/placeholder.png")
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Title
        title_label = QLabel("Photidy")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Version & copyright info
        info_label = QLabel(f"Version {__version__}<br>&copy; 2025 Rob Webb")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_font = QFont()
        info_font.setPointSize(10)
        info_label.setFont(info_font)
        layout.addWidget(info_label)

        # Button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(about.accept)
        layout.addWidget(ok_button)

        about.exec()
