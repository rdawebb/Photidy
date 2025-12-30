"""Custom menubar for the application"""

import wx


class MenuBar(wx.MenuBar):
    """Custom menubar for the application"""

    def __init__(self):
        """Initialise the menubar"""
        super().__init__()

        file_menu = wx.Menu()
        self.exit_item = file_menu.Append(wx.ID_EXIT, "&Exit\tCtrl+Q", "Exit the app")

        self.Append(file_menu, "&File")
