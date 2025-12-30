"""Main application window"""

import wx

from src.ui.menubar import MenuBar


class MainWindow(wx.Frame):
    """Main application window"""

    def __init__(self):
        """Initialise the main window"""
        super().__init__(parent=None, title="📷 Photidy")
        menubar = MenuBar()

        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_MENU, self.on_exit, menubar.exit_item)

        self.Centre()

    def on_exit(self, event):
        """Handle the exit menu item"""
        self.Close()
