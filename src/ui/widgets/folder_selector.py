"""Folder selector widget for selecting directories"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QWidget

from .custom_button import CustomButton


class FolderSelector(QWidget):
    """Folder selector widget for selecting directories"""

    folderSelected = Signal(str)

    def __init__(self, parent=None):
        """Initialise the folder selector widget

        Args:
            parent (QWidget, optional): The parent widget
        """
        super().__init__(parent)
        self._layout = QHBoxLayout(self)

        self.line_edit = QLineEdit(self)
        self.line_edit.setClearButtonEnabled(True)
        self.line_edit.setPlaceholderText("Enter a folder path")

        self.browse_button = CustomButton("Browse", self)
        self.browse_button.setToolTip("Browse for folder")
        self._layout.addWidget(self.line_edit)
        self._layout.addWidget(self.browse_button)
        self.browse_button.clicked.connect(self.open_folder_dialog)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Enable touch events if supported
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)

    def open_folder_dialog(self):
        """Open a folder selection dialog"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder:
            self.line_edit.setText(folder)
            self.folderSelected.emit(folder)

    def dragEnterEvent(self, event):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Handle drag move events"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle drop events"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    self.line_edit.setText(url.toLocalFile())
                    self.folderSelected.emit(url.toLocalFile())
                    break

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
