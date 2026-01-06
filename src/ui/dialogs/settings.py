"""Settings dialog for advanced options"""

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    """Settings dialog for advanced options"""

    def __init__(self, parent=None):
        """Initialise the settings dialog"""
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        form = QFormLayout()
        form.setSpacing(15)

        # Default organisation type
        self.org_type = QComboBox()
        self.org_type.addItems(["Date First", "Location First"])
        form.addRow("Default Organisation:", self.org_type)

        self.date_precision = QComboBox()
        self.date_precision.addItems(["Year", "Year/Month", "Year/Month/Day"])
        form.addRow("Date Precision:", self.date_precision)

        self.location_precision = QComboBox()
        self.location_precision.addItems(["Country", "City", "Precise"])
        form.addRow("Location Precision:", self.location_precision)

        self.thread_count = QSpinBox()
        self.thread_count.setRange(1, 16)
        self.thread_count.setValue(4)
        form.addRow("Processing Threads:", self.thread_count)

        self.auto_subdirs = QCheckBox("Automatically scan subdirectories")
        self.auto_subdirs.setChecked(True)
        form.addRow("", self.auto_subdirs)

        self.create_backup = QCheckBox("Create backup before organising")
        form.addRow("", self.create_backup)

        layout.addLayout(form)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        ).clicked.connect(self.restore_defaults)

        layout.addWidget(button_box)

    def load_settings(self):
        """Load the saved settings"""
        settings = QSettings("Photidy", "Settings")
        self.org_type.setCurrentText(str(settings.value("org_type", "Date First")))
        self.date_precision.setCurrentText(
            str(settings.value("date_precision", "Year/Month/Day"))
        )
        self.location_precision.setCurrentText(
            str(settings.value("location_precision", "City"))
        )

    def save_settings(self):
        """Save the current settings"""
        settings = QSettings("Photidy", "Settings")
        settings.setValue("org_type", self.org_type.currentText())
        settings.setValue("date_precision", self.date_precision.currentText())
        settings.setValue("location_precision", self.location_precision.currentText())

    def restore_defaults(self):
        """Restore default settings"""
        self.org_type.setCurrentText("Date First")
        self.date_precision.setCurrentText("Year/Month/Day")
        self.location_precision.setCurrentText("City")
        self.thread_count.setValue(4)
        self.auto_subdirs.setChecked(True)
        self.create_backup.setChecked(False)

    def accept(self):
        """Accept the dialog and save settings"""
        self.save_settings()
        super().accept()
