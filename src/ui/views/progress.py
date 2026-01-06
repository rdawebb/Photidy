"""Organisation progress view for the application GUI"""

from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class ProgressView(QWidget):
    """Progress view for displaying the organisation progress"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(0, 50, 0, 50)

        layout.addStretch()

        self.title = QLabel("Organising Your Photos")
        # ... set font, alignment, etc. ...
        layout.addWidget(self.title)

        self.status_label = QLabel("Processing...")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(12)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.current_file_label = QLabel("")
        layout.addWidget(self.current_file_label)

        layout.addStretch()

        self.warning = QLabel("Please don't close the application while organising")
        layout.addWidget(self.warning)

    def set_progress(self, value, maximum):
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)

    def set_status(self, text):
        self.status_label.setText(text)

    def set_current_file(self, filename):
        self.current_file_label.setText(f"Current: {filename}")
