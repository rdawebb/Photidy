"""Main application window"""

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.dialogs import AboutDialog, ConfirmDialog, SettingsDialog
from src.ui.threads import OrganiserThread, ScannerThread
from src.ui.utils.constants import (
    APP_TITLE,
    MENU_ABOUT,
    MENU_EXIT,
    MENU_FILE,
    MENU_HELP,
    MENU_SETTINGS,
    SHORTCUT_EXIT,
    SHORTCUT_SETTINGS,
)
from src.ui.utils.svg_utils import svg_icon_with_palette_color
from src.ui.views import ProgressView, ResultsView, SetupView, SummaryView
from src.ui.widgets import CustomButton


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)

        # Set up the native app menubar
        menubar = self.menuBar()
        menubar.clear()

        # File menu
        file_menu = menubar.addMenu(MENU_FILE)
        self.exit_action = QAction(MENU_EXIT, self)
        self.exit_action.setShortcut(SHORTCUT_EXIT)
        self.exit_action.triggered.connect(self._on_exit)
        self.exit_action.setToolTip("Exit the app")
        self.exit_action.setProperty("accessibleName", "Exit Action")
        file_menu.addAction(self.exit_action)

        # Preferences/Settings
        self.prefs_action = QAction(MENU_SETTINGS, self)
        self.prefs_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.prefs_action.setShortcut(SHORTCUT_SETTINGS)
        self.prefs_action.triggered.connect(self._on_preferences)
        self.prefs_action.setToolTip("Open application settings")
        self.prefs_action.setProperty("accessibleName", "Preferences Action")
        file_menu.addAction(self.prefs_action)

        # Help menu
        help_menu = menubar.addMenu(MENU_HELP)
        self.about_action = QAction(MENU_ABOUT, self)
        self.about_action.setMenuRole(QAction.MenuRole.AboutRole)
        self.about_action.triggered.connect(self._on_about)
        self.about_action.setToolTip("Show information about Photidy")
        self.about_action.setProperty("accessibleName", "About Action")
        help_menu.addAction(self.about_action)

        # Instantiate central stacked widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Stacked widget for different views
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        main_layout.addStretch()

        # Navigation buttons
        self.back_button = CustomButton("Back")
        self.next_button = CustomButton("Next")

        palette = self.back_button.palette()
        back_icon = svg_icon_with_palette_color(
            "src/ui/assets/inline-left.svg",
            palette.color(QPalette.ColorRole.ButtonText),
        )
        forward_icon = svg_icon_with_palette_color(
            "src/ui/assets/inline-right.svg",
            palette.color(QPalette.ColorRole.ButtonText),
        )
        self.back_button.setIcon(back_icon)
        self.next_button.setIcon(forward_icon)
        self.next_button.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.back_button.clicked.connect(self._go_back)
        self.next_button.clicked.connect(self._go_forward)

        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.back_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_button)
        main_layout.addLayout(nav_layout)

        # Views
        self.setup_view = SetupView()
        self.results_view = ResultsView()
        self.progress_view = ProgressView()
        self.summary_view = SummaryView()

        self.stacked_widget.addWidget(self.setup_view)
        self.stacked_widget.addWidget(self.results_view)
        self.stacked_widget.addWidget(self.progress_view)
        self.stacked_widget.addWidget(self.summary_view)

        self.stacked_widget.currentChanged.connect(self._nav_visibility)
        self._nav_visibility(self.stacked_widget.currentIndex())

        self.setup_view.scan_requested.connect(self.start_scan)
        self.results_view.organise_requested.connect(self.start_organise)
        self.summary_view.open_output_folder_requested.connect(self.open_output_folder)
        self.summary_view.new_scan_requested.connect(self.reset_to_start)

        # Status bar
        self.statusBar().showMessage("Ready")

        self.scan_results: dict = {}
        self.scanner_thread = None
        self.organiser_thread = None

        # Misc settings
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self.resize(600, 400)

    def center_window(self):
        """Center the window on screen"""
        screen = self.screen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

    def _is_process_running(self):
        """Check if a process is currently running"""
        if (self.scanner_thread and self.scanner_thread.isRunning()) or (
            self.organiser_thread and self.organiser_thread.isRunning()
        ):
            return True
        return False

    def _on_exit(self):
        """Handle the exit menu item"""
        if self._is_process_running():
            self.hide()
        else:
            QApplication.quit()

    def closeEvent(self, event):
        """Handle the close event"""
        if self._is_process_running():
            self.hide()
            event.ignore()
        else:
            QApplication.quit()

    def _on_preferences(self):
        """Handle the preferences menu item"""
        dialog = SettingsDialog(self)
        if dialog.exec():
            self._apply_settings()

    def _apply_settings(self):
        """Apply the settings from the preferences dialog (placeholder)"""
        settings = QSettings("Photidy", "Settings")
        settings.setValue("some_setting", "some_value")

    def _on_about(self):
        """Handle the about menu item"""
        dialog = AboutDialog(self)
        dialog.exec()

    def _go_back(self):
        """Handle the back button click"""
        idx = self.stacked_widget.currentIndex()
        if idx > 0:
            self.stacked_widget.setCurrentIndex(idx - 1)

    def _go_forward(self):
        """Handle the forward button click"""
        idx = self.stacked_widget.currentIndex()
        if idx < self.stacked_widget.count() - 1:
            self.stacked_widget.setCurrentIndex(idx + 1)

    def _nav_visibility(self, index):
        """Update the visibility of the navigation buttons"""
        self.back_button.setVisible(index > 0)
        self.next_button.setVisible(index < self.stacked_widget.count() - 1)

    def start_scan(self, source_dir):
        """Start the directory scanning process"""
        try:
            self.stacked_widget.setCurrentWidget(self.progress_view)
            self.progress_view.set_status("Scanning...")
            self.progress_view.set_progress(0, 0)  # Spinner mode
            self.progress_view.set_current_file("")

            self.scanner_thread = ScannerThread(source_dir)
            self.scanner_thread.progress.connect(self.update_scan_progress)
            self.scanner_thread.finished.connect(self.scan_completed)
            self.scanner_thread.start()
            self.statusBar().showMessage("Scanning directory...")

        except Exception as e:
            self.statusBar().showMessage(f"Failed to start scan: {e}")

    def update_scan_progress(self, count, filename):
        """Update the progress view during scanning"""
        self.progress_view.set_status(f"Scanned... {count} files")
        self.progress_view.set_current_file(filename)

    def scan_completed(self, results):
        """Handle the completion of the scan"""
        try:
            self.scan_results = results
            self.results_view.set_results(results)
            self.stacked_widget.setCurrentWidget(self.results_view)
            self.statusBar().showMessage(
                f"Found {results.get('images_count', 0)} photos"
            )
            self.scanner_thread = None

        except Exception as e:
            self.statusBar().showMessage(f"Failed to process scan results: {e}")

    def start_organise(self, options):
        """Start the photo organising process"""
        try:
            output_dir = options["output_dir"]
            dialog = ConfirmDialog(self.scan_results, options, output_dir, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            self.stacked_widget.setCurrentWidget(self.progress_view)
            self.progress_view.set_status("Organising photos...")
            file_paths = self.scan_results.get("image_files", [])
            self.progress_view.set_progress(0, len(file_paths))
            self.progress_view.set_current_file("")

            self.organiser_thread = OrganiserThread(
                file_paths, options["output_dir"], options
            )
            self.organiser_thread.progress.connect(self.update_organise_progress)
            self.organiser_thread.finished.connect(self.organise_completed)
            self.organiser_thread.start()
            self.statusBar().showMessage("Organising photos...")

        except Exception as e:
            self.statusBar().showMessage(f"Failed to start organisation: {e}")

    def update_organise_progress(self, current, total, filename):
        """Update the progress view during organising"""
        self.progress_view.set_progress(current, total)
        self.progress_view.set_status(f"Processing {current} of {total} photos")
        self.progress_view.set_current_file(filename)

    def organise_completed(self, results):
        """Handle the completion of the organise process"""
        try:
            self.summary_view.set_summary(results)
            self.stacked_widget.setCurrentWidget(self.summary_view)
            self.statusBar().showMessage("Organisation complete!")
            self.organiser_thread = None

        except Exception as e:
            self.statusBar().showMessage(f"Failed to complete organisation: {e}")

    def open_output_folder(self):
        """Open the output folder in the native file explorer"""
        import platform
        import subprocess

        output_dir = self.results_view.folder_selector.get_selected_folder()
        if output_dir:
            try:
                if platform.system() == "Windows":
                    subprocess.Popen(f'explorer "{output_dir}"')
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", output_dir])
                else:
                    subprocess.Popen(["xdg-open", output_dir])

            except Exception as e:
                self.statusBar().showMessage(f"Failed to open folder: {e}")

    def reset_to_start(self):
        """Reset the application to the initial state"""
        self.scan_results = {}
        self.setup_view.folder_selector.clear_selection()
        self.results_view.folder_selector.clear_selection()
        self.stacked_widget.setCurrentWidget(self.setup_view)
        self.statusBar().showMessage("Ready")
