"""Results view for displaying scan results"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.custom_button import CustomButton
from src.ui.widgets.folder_selector import FolderSelector


class ResultsView(QWidget):
    """Results view for displaying scan results"""

    organise_requested = Signal(dict)
    output_dir_selected = Signal(str)

    def __init__(self, parent=None):
        """Initialise the results view"""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Results summary
        self.results_label = QLabel()
        self.results_label.setWordWrap(True)
        layout.addWidget(self.results_label)

        # Inaccessible files
        self.inaccessible_widget = QWidget()
        inac_layout = QVBoxLayout(self.inaccessible_widget)
        inac_label = QLabel("<b>Inaccessible files:</b>")
        inac_layout.addWidget(inac_label)
        self.inaccessible_text = QTextEdit()
        self.inaccessible_text.setMaximumHeight(100)
        self.inaccessible_text.setReadOnly(True)
        inac_layout.addWidget(self.inaccessible_text)
        self.inaccessible_widget.setVisible(False)
        layout.addWidget(self.inaccessible_widget)

        # Organisation options
        org_type_label = QLabel("Organisation Type:")
        layout.addWidget(org_type_label)
        self.org_type_group = QButtonGroup()
        self.date_first_radio = QRadioButton("Date First")
        self.location_first_radio = QRadioButton("Location First")
        self.org_type_group.addButton(self.date_first_radio, 0)
        self.org_type_group.addButton(self.location_first_radio, 1)
        self.date_first_radio.setChecked(True)
        layout.addWidget(self.date_first_radio)
        layout.addWidget(self.location_first_radio)

        precision_label = QLabel("Precision:")
        layout.addWidget(precision_label)
        self.precision_combo = QComboBox()
        self.precision_combo.addItems(["Year/Month/Day", "Year/Month", "Year Only"])
        layout.addWidget(self.precision_combo)

        # Output directory
        output_label = QLabel("Output Directory:")
        layout.addWidget(output_label)
        output_group = QGroupBox()
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(10)

        dir_layout = QHBoxLayout()
        self.folder_selector = FolderSelector()
        self.folder_selector.folderSelected.connect(self.on_output_folder_selected)
        self.folder_selector.line_edit.textChanged.connect(self.on_folder_text_changed)
        self.folder_selector.setToolTip("Select the folder to save organised photos")
        self.folder_selector.setProperty("accessibleName", "Output Folder Selector")
        dir_layout.addWidget(self.folder_selector)

        output_layout.addLayout(dir_layout)

        help_text = QLabel("Select the folder to save organised photos")
        help_text.setStyleSheet("color: gray; font-size: 11px;")
        help_text.setWordWrap(True)
        output_layout.addWidget(help_text)

        layout.addWidget(output_group)

        # Organise button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.organise_btn = CustomButton("Organise Photos")
        self.organise_btn.setMinimumSize(180, 44)
        self.organise_btn.setEnabled(False)
        self.organise_btn.clicked.connect(self.on_organise_clicked)
        button_layout.addWidget(self.organise_btn)

        layout.addLayout(button_layout)

    def set_results(self, results):
        """Set the results summary and details"""
        self.results_label.setText(
            f"<b>Total files scanned:</b> {results['total_files']}<br>"
            f"<b>Image files found:</b> {results['images_count']}<br>"
            f"<b>Estimated organisation time:</b> ??? seconds"
        )
        if results.get("inaccessible"):
            self.inaccessible_widget.setVisible(True)
            self.inaccessible_text.setText("\n".join(results["inaccessible"]))
        else:
            self.inaccessible_widget.setVisible(False)

    def on_output_folder_selected(self, folder):
        """Handle output folder selection"""
        self.organise_btn.setEnabled(bool(folder))

    def on_folder_text_changed(self, text):
        """Handle folder text changes (including clearing)"""
        self.organise_btn.setEnabled(bool(text))

    def on_organise_clicked(self):
        """Handle organise button click"""
        options = {
            "type": "Date First"
            if self.date_first_radio.isChecked()
            else "Location First",
            "precision": self.precision_combo.currentText(),
            "output_dir": self.folder_selector.get_selected_folder(),
        }
        self.organise_requested.emit(options)
