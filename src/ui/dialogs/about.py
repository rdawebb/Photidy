"""About dialog for application information"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from src import __version__
from src.ui.utils.constants import ABOUT_COPYRIGHT, ABOUT_ICON_PATH


class AboutDialog(QDialog):
    """About dialog for application information"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")

        layout = QVBoxLayout(self)

        # Icon
        icon_label = QLabel()
        pixmap = QPixmap(ABOUT_ICON_PATH)
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
        info_label = QLabel(f"Version {__version__}<br>{ABOUT_COPYRIGHT}")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_font = QFont()
        info_font.setPointSize(10)
        info_label.setFont(info_font)
        layout.addWidget(info_label)

        # Button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)
