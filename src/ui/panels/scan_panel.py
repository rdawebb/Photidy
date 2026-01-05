"""Panel for scanning files in a given directory"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.organiser import scan_directory
from src.ui.widgets.button import Button
from src.ui.widgets.folder_selector import FolderSelector


class ScanPanel(QWidget):
    """Panel for scanning files in a given directory"""

    def __init__(self, parent=None):
        """Initialise the scan panel widget

        Args:
            parent (QWidget, optional): The parent widget
        """
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self.folder_selector = FolderSelector(self)

        self.result_table = QTableWidget(self)
        self.result_table.setColumnCount(2)
        self.result_table.horizontalHeader().setVisible(False)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        self.result_table.setMaximumWidth(240)
        self.result_table.hide()

        self.scan_button = Button("Scan", self)
        self.scan_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.scan_button.setToolTip(
            "Scan the selected folder and subfolders for photos"
        )

        self._layout.addWidget(self.folder_selector)
        self._layout.addWidget(
            self.scan_button,
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )
        self._layout.addWidget(
            self.result_table,
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        )

        self.scan_button.clicked.connect(self.on_scan_clicked)

    def on_scan_clicked(self):
        """Handle the scan button click event"""
        folder = self.folder_selector.get_selected_folder()
        results = scan_directory(folder)
        self.display_results(results)

    def display_results(self, results: dict):
        """Display the scan results in the table

        Args:
            results (dict): The scan results containing photo files and counts
        """
        rows = []
        if results.get("photos_count", 0) > 0:
            rows.append(("Photos", results.get("photos_count", 0)))
        if results.get("other_count", 0) > 0:
            rows.append(("Other", results.get("other_count", 0)))
        if results.get("inaccessible_count", 0) > 0:
            rows.append(("Inaccessible", results.get("inaccessible_count", 0)))

        rows.append(("Total", results.get("total_files", 0)))

        self.result_table.setRowCount(len(rows))
        for row_idx, (label, value) in enumerate(rows):
            self.result_table.setItem(row_idx, 0, QTableWidgetItem(label))
            self.result_table.setItem(row_idx, 1, QTableWidgetItem(str(value)))

        self.result_table.resizeRowsToContents()
        total_height = (
            self.result_table.verticalHeader().length()
            + self.result_table.horizontalHeader().height()
            + 3  # buffer for frame/grid/margins
        )
        self.result_table.setFixedHeight(total_height)

        self.result_table.show()
