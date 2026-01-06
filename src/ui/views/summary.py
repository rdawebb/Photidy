"""View for displaying the organisation summary"""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton


class SummaryView(QWidget):
    """View for displaying the organisation summary"""

    open_output_folder_requested = Signal()
    new_scan_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Success message
        success_icon = QLabel("✓")
        success_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_icon.setStyleSheet(
            "color: #28a745; font-size: 48px; font-weight: bold;"
        )
        layout.addWidget(success_icon)

        success_title = QLabel("Organisation Complete!")
        # ... set font, alignment, etc. ...
        layout.addWidget(success_title)

        # Summary details
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        layout.addStretch()

        # Action buttons
        button_layout = QHBoxLayout()
        open_folder_btn = QPushButton("Open Output Folder")
        open_folder_btn.clicked.connect(self.open_output_folder_requested.emit)
        button_layout.addWidget(open_folder_btn)

        button_layout.addStretch()

        new_scan_btn = QPushButton("Organise More Photos")
        new_scan_btn.clicked.connect(self.new_scan_requested.emit)
        button_layout.addWidget(new_scan_btn)

        layout.addLayout(button_layout)

    def set_summary(self, results):
        # Update summary_label with results dict
        self.summary_label.setText(
            f"<b>Photos organised:</b> {results['organised']}<br>"
            f"<b>Photos skipped:</b> {results['skipped']}<br>"
            f"<b>Output directory:</b> {results['output_dir']}"
        )
        if results.get("errors"):
            self.summary_label.setText(
                self.summary_label.text()
                + f"<br><br><b>Errors encountered:</b> {len(results['errors'])}"
            )
