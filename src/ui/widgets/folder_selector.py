"""Folder selector widget for selecting directories"""

import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFileDialog, QLineEdit, QHBoxLayout, QWidget

from .button import Button


class FolderSelector(QWidget):
    """Folder selector widget for selecting directories"""

    folderSelected = Signal(str)

    def __init__(self, parent=None):
        """Initialise the folder selector widget

        Args:
            parent (QWidget, optional): The parent widget
        """
        super().__init__(parent)
        self.layout = QHBoxLayout(self)

        self.line_edit = QLineEdit(self)
        self.line_edit.setClearButtonEnabled(True)
        self.line_edit.setPlaceholderText("Enter a folder path")

        self.browse_button = Button("Browse", self)
        self.browse_button.setToolTip("Browse for folder")
        self.layout.addWidget(self.line_edit)
        self.layout.addWidget(self.browse_button)
        self.browse_button.clicked.connect(self.open_folder_dialog)

        if sys.platform == "darwin":
            self.setAttribute(Qt.WA_AcceptTouchEvents)

    def open_folder_dialog(self):
        """Open a folder selection dialog"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder:
            self.line_edit.setText(folder)
            self.folderSelected.emit(folder)

    def get_selected_folder(self) -> str:
        """Get the currently selected folder

        Returns:
            str: The selected folder path
        """
        return self.line_edit.text()

    def set_selected_folder(self, folder: str) -> None:
        """Set the currently selected folder

        Args:
            folder (str): The folder path to set
        """
        self.line_edit.setText(folder)
        self.folderSelected.emit(folder)

    def clear_selection(self) -> None:
        """Clear the currently selected folder"""
        self.line_edit.clear()
