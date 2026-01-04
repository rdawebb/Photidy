"""Button widget for triggering actions"""

from PySide6.QtWidgets import QPushButton


class Button(QPushButton):
    """Custom button widget for triggering actions"""

    def __init__(self, text: str, parent=None):
        """Initialise the button with text and parent widget

        Args:
            text (str): The text to display on the button
            parent (QWidget, optional): The parent widget
        """
        super().__init__(text, parent)
