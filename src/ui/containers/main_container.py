"""Container for the main application window"""

from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.ui.panels.scan_panel import ScanPanel


class MainContainer(QWidget):
    """Container for the main application window"""

    def __init__(self, parent=None):
        """Initialise the main container widget

        Args:
            parent (QWidget, optional): The parent widget
        """
        super().__init__(parent)
        self._process_running = False
        self._layout = QVBoxLayout(self)
        self.scan_panel = ScanPanel(self)
        self._layout.addWidget(self.scan_panel)

    def is_process_running(self) -> bool:
        """Check if a process is currently running

        Returns:
            bool: True if a process is running, False otherwise
        """
        return self._process_running

    def start_process(self) -> None:
        """Set the process running state to True"""
        self._process_running = True

    def stop_process(self) -> None:
        """Set the process running state to False"""
        self._process_running = False
