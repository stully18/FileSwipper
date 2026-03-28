"""Main application window that orchestrates all screens."""

from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core import FileInfo
from core.undo_manager import UndoManager
from gui.dialogs import FirstTimeSetupDialog, SettingsDialog
from gui.folder_selection import FolderSelectionScreen
from gui.preview import PreviewScreen
from gui.progress import ProgressScreen
from gui.suggestions import SuggestionsScreen

SETTINGS_ORG = "AIFileOrganizer"
SETTINGS_APP = "AIFileOrganizer"

STEP_LABELS = [
    "Select Folder",
    "Review Suggestions",
    "Preview",
    "Organize",
]


class MainWindow(QMainWindow):
    """Application shell that orchestrates the four workflow screens."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI File Organizer")
        self.setMinimumSize(800, 600)

        # ------------------------------------------------------------------
        # State
        # ------------------------------------------------------------------
        self.files: list[FileInfo] = []
        self.categories: dict[str, list[FileInfo]] = {}
        self.source_dir: str = ""

        # ------------------------------------------------------------------
        # Central widget
        # ------------------------------------------------------------------
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Breadcrumb
        self._breadcrumb_widget, self._breadcrumb_labels = self._create_breadcrumb()
        main_layout.addWidget(self._breadcrumb_widget)

        # Stacked widget with the four screens
        self._stack = QStackedWidget()

        self._folder_screen = FolderSelectionScreen()
        self._suggestions_screen = SuggestionsScreen()
        self._preview_screen = PreviewScreen()
        self._progress_screen = ProgressScreen()

        self._stack.addWidget(self._folder_screen)      # index 0
        self._stack.addWidget(self._suggestions_screen)  # index 1
        self._stack.addWidget(self._preview_screen)      # index 2
        self._stack.addWidget(self._progress_screen)     # index 3

        main_layout.addWidget(self._stack, 1)

        # ------------------------------------------------------------------
        # Signal wiring
        # ------------------------------------------------------------------
        self._folder_screen.analysis_complete.connect(self._on_analysis_complete)

        self._suggestions_screen.suggestions_accepted.connect(
            self._on_suggestions_accepted
        )
        self._suggestions_screen.back_requested.connect(
            lambda: self._navigate_to(0)
        )

        self._preview_screen.confirmed.connect(self._on_preview_confirmed)
        self._preview_screen.back_requested.connect(
            lambda: self._navigate_to(1)
        )

        self._progress_screen.start_over_requested.connect(self._on_start_over)
        self._progress_screen.undo_completed.connect(self._on_undo_completed)

        # ------------------------------------------------------------------
        # Menu bar
        # ------------------------------------------------------------------
        self._create_menus()

        # Start on the first page
        self._navigate_to(0)

    # ------------------------------------------------------------------
    # Menu creation
    # ------------------------------------------------------------------

    def _create_menus(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        settings_action = QAction("&Settings", self)
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        undo_action = QAction("&Undo Last Operation", self)
        undo_action.triggered.connect(self._undo_last)
        file_menu.addAction(undo_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _navigate_to(self, index: int):
        """Switch the stacked widget to *index* and update the breadcrumb."""
        self._stack.setCurrentIndex(index)
        self._update_breadcrumb(index)

    # ------------------------------------------------------------------
    # Breadcrumb
    # ------------------------------------------------------------------

    def _create_breadcrumb(self) -> tuple[QWidget, list[QLabel]]:
        """Build the step-indicator bar and return (widget, label_list)."""
        widget = QWidget()
        widget.setStyleSheet(
            "QWidget { background-color: #f5f5f5; border-bottom: 1px solid #e0e0e0; }"
        )
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(0)

        labels: list[QLabel] = []
        for i, text in enumerate(STEP_LABELS):
            if i > 0:
                separator = QLabel("  >  ")
                separator.setStyleSheet("color: #9e9e9e;")
                layout.addWidget(separator)

            label = QLabel(text)
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            # Store the step index on the label so we can navigate on click
            label.setProperty("step_index", i)
            label.mousePressEvent = self._make_breadcrumb_click_handler(i)
            labels.append(label)
            layout.addWidget(label)

        layout.addStretch()
        return widget, labels

    def _make_breadcrumb_click_handler(self, index: int):
        """Return a mouse-press handler that navigates to a past step."""

        def handler(event):
            current = self._stack.currentIndex()
            # Only allow clicking on past (already-visited) steps
            if index < current:
                self._navigate_to(index)

        return handler

    def _update_breadcrumb(self, current_index: int):
        """Highlight the current step, grey out future steps, style past steps."""
        for i, label in enumerate(self._breadcrumb_labels):
            if i == current_index:
                label.setStyleSheet(
                    "color: #2196F3; font-weight: bold; font-size: 11pt;"
                )
                label.setCursor(Qt.CursorShape.ArrowCursor)
            elif i < current_index:
                label.setStyleSheet(
                    "color: #1976D2; font-size: 11pt; text-decoration: underline;"
                )
                label.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                label.setStyleSheet("color: #9e9e9e; font-size: 11pt;")
                label.setCursor(Qt.CursorShape.ArrowCursor)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_analysis_complete(self, files: list):
        """Store scanned files, extract source dir, navigate to suggestions."""
        self.files = files
        if files:
            self.source_dir = str(files[0].path.parent)
        self._navigate_to(1)
        self._suggestions_screen.load_suggestions(
            files, self._get_api_key(), self._get_model()
        )

    def _on_suggestions_accepted(self, categories: dict):
        """Store approved categories, navigate to preview."""
        self.categories = categories
        self._navigate_to(2)
        self._preview_screen.load_preview(categories, self.source_dir)

    def _on_preview_confirmed(self):
        """Navigate to progress screen and start moving files."""
        self._navigate_to(3)
        self._progress_screen.start_moving(
            Path(self.source_dir), self.categories
        )

    def _on_start_over(self):
        """Reset all screens and navigate back to folder selection."""
        self.files = []
        self.categories = {}
        self.source_dir = ""

        self._folder_screen.reset()
        self._suggestions_screen.reset()
        self._preview_screen.reset()
        self._progress_screen.reset()

        self._navigate_to(0)

    def _on_undo_completed(self):
        """Handle undo completion from the progress screen."""
        # Nothing extra needed; the ProgressScreen already shows the result.
        pass

    # ------------------------------------------------------------------
    # Menu actions
    # ------------------------------------------------------------------

    def _open_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()

    def _undo_last(self):
        """Undo the most recent file-move operation via UndoManager."""
        manager = UndoManager()
        try:
            succeeded, failed = manager.undo_last()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Undo Error",
                f"An error occurred while undoing:\n\n{exc}",
            )
            return

        if succeeded == 0 and failed == 0:
            QMessageBox.information(
                self, "Undo", "There are no operations to undo."
            )
        elif failed == 0:
            QMessageBox.information(
                self,
                "Undo Complete",
                f"Successfully restored {succeeded} "
                f"file{'s' if succeeded != 1 else ''} to their original locations.",
            )
        else:
            QMessageBox.warning(
                self,
                "Undo Partially Complete",
                f"Restored {succeeded} file{'s' if succeeded != 1 else ''}, "
                f"but {failed} file{'s' if failed != 1 else ''} could not be moved back.",
            )

    def _show_about(self):
        """Show an About dialog."""
        QMessageBox.about(
            self,
            "About AI File Organizer",
            "AI File Organizer\n\n"
            "Intelligently organize your files into folders using AI.\n\n"
            "Powered by Google Gemini.",
        )

    # ------------------------------------------------------------------
    # First-run check
    # ------------------------------------------------------------------

    def _check_first_run(self):
        """If no API key is configured, show the first-time setup dialog."""
        api_key = self._get_api_key()
        if not api_key:
            dialog = FirstTimeSetupDialog(self)
            dialog.exec()

    # ------------------------------------------------------------------
    # Settings helpers
    # ------------------------------------------------------------------

    def _get_api_key(self) -> str:
        """Read the Gemini API key from QSettings."""
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        return settings.value("api_key", "", type=str)

    def _get_model(self) -> str:
        """Read the AI model from QSettings, defaulting to gemini-2.0-flash."""
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        return settings.value("model", "gemini-2.0-flash-lite", type=str)
