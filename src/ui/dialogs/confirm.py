"""Confirmation dialog before organising"""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout


class ConfirmDialog(QDialog):
    """Confirmation dialog before organising"""

    def __init__(self, scan_results, options, output_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Organisation")
        self.setMinimumWidth(450)
        self.setup_ui(scan_results, options, output_dir)

    def setup_ui(self, scan_results, options, output_dir):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        title = QLabel("Ready to organise your photos")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.Medium)
        title.setFont(title_font)
        layout.addWidget(title)

        summary = QLabel(
            f"<b>Photos to organise:</b> {scan_results.get('image_files', 0)}<br>"
            f"<b>Organisation type:</b> {options.get('type', 'Date First')}<br>"
            f"<b>Precision:</b> {options.get('precision', 'Year/Month/Day')}<br>"
            f"<b>Output directory:</b> {output_dir}<br><br>"
            f"<b>Estimated time:</b> ~{scan_results.get('estimated_time', 0)} seconds"
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        warning = QLabel(
            "⚠️ This operation will move files. Make sure you have a backup if needed."
        )
        warning.setStyleSheet(
            "color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 4px;"
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
