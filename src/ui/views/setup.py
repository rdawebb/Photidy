"""Setup view for the application GUI"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.custom_button import CustomButton
from src.ui.widgets.folder_selector import FolderSelector


class SetupView(QWidget):
    """Setup view for the application GUI"""

    scan_requested = Signal(str)

    def __init__(self, parent=None):
        """Initialise the setup view"""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Source directory selection
        source_label = QLabel("Source Directory:")
        layout.addWidget(source_label)
        source_group = QGroupBox()
        source_layout = QVBoxLayout(source_group)
        source_layout.setSpacing(10)

        dir_layout = QHBoxLayout()
        self.folder_selector = FolderSelector()
        self.folder_selector.folderSelected.connect(self.on_folder_selected)
        self.folder_selector.line_edit.textChanged.connect(self.on_folder_text_changed)
        self.folder_selector.setToolTip(
            "Select the folder containing photos to organise"
        )
        self.folder_selector.setProperty("accessibleName", "Source Folder Selector")
        dir_layout.addWidget(self.folder_selector)

        source_layout.addLayout(dir_layout)

        help_text = QLabel(
            "Select the folder containing photos you want to organise (subfolders will be scanned automatically)"
        )
        help_text.setStyleSheet("color: gray; font-size: 11px;")
        help_text.setWordWrap(True)
        source_layout.addWidget(help_text)

        layout.addWidget(source_group)

        # Scan button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.scan_btn = CustomButton("Scan Directory")
        self.scan_btn.setMinimumSize(180, 44)
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self.on_scan_clicked)
        button_layout.addWidget(self.scan_btn)

        layout.addLayout(button_layout)

        # Progress section (hidden initially)
        self.scan_progress_widget = QWidget()
        self.scan_progress_widget.setVisible(False)
        progress_layout = QVBoxLayout(self.scan_progress_widget)
        progress_layout.setSpacing(10)

        self.scan_progress_label = QLabel("Scanning...")
        progress_layout.addWidget(self.scan_progress_label)

        self.scan_progress_bar = QProgressBar()
        self.scan_progress_bar.setMinimumHeight(6)
        self.scan_progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.scan_progress_bar)

        layout.addWidget(self.scan_progress_widget)

        layout.addStretch()

    def on_folder_selected(self, folder):
        """Handle folder selection from the folder selector"""
        self.scan_btn.setEnabled(bool(folder))

    def on_folder_text_changed(self, text):
        """Handle folder text changes (including clearing)"""
        self.scan_btn.setEnabled(bool(text))

    def on_scan_clicked(self):
        """Handle the scan button click"""
        source_dir = self.folder_selector.get_selected_folder()
        if source_dir:
            self.scan_requested.emit(source_dir)
