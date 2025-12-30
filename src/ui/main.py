"""Main GUI entry point"""

import wx

from src.ui.frame_main import MainWindow


def main():
    app = wx.App()
    frame = MainWindow()
    frame.Show()
    app.SetTopWindow(frame)
    app.MainLoop()


if __name__ == "__main__":
    main()
