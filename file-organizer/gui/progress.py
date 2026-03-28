"""Screen 4: Progress during file moving and completion summary."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QProgressBar,
    QMessageBox,
    QStackedWidget,
    QScrollArea,
    QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, QThread, Qt, QUrl
from PyQt6.QtGui import QFont, QDesktopServices

from core import FileInfo
from core.file_mover import FileMover
from core.undo_manager import UndoManager
from utils.file_icons import get_category_icon


class ProgressScreen(QWidget):
    """Screen 4: shows progress during file moving and the completion summary."""

    completed = pyqtSignal()
    undo_completed = pyqtSignal()
    start_over_requested = pyqtSignal()

    # ------------------------------------------------------------------
    # Inner worker threads
    # ------------------------------------------------------------------

    class MoveWorker(QThread):
        """Runs file-move operations in a background thread."""

        progress = pyqtSignal(int, int, str)  # current, total, filename
        finished = pyqtSignal(list, list)  # moves, errors
        error = pyqtSignal(str)

        def __init__(self, source_dir: Path, categories: dict[str, list[FileInfo]]):
            super().__init__()
            self._source_dir = source_dir
            self._categories = categories

        def run(self):
            try:
                mover = FileMover(self._source_dir)
                moves = mover.execute_plan(
                    self._categories,
                    progress_callback=lambda cur, tot, name: self.progress.emit(
                        cur, tot, name
                    ),
                )
                self.finished.emit(list(moves), list(mover.errors))
            except Exception as exc:
                self.error.emit(str(exc))

    class UndoWorker(QThread):
        """Runs undo operations in a background thread."""

        finished = pyqtSignal(int, int)  # succeeded, failed
        error = pyqtSignal(str)

        def run(self):
            try:
                manager = UndoManager()
                succeeded, failed = manager.undo_last()
                self.finished.emit(succeeded, failed)
            except Exception as exc:
                self.error.emit(str(exc))

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_dir: Path | None = None
        self._categories: dict[str, list[FileInfo]] = {}
        self._move_worker: ProgressScreen.MoveWorker | None = None
        self._undo_worker: ProgressScreen.UndoWorker | None = None
        self._completed_moves: list[tuple[Path, Path]] = []
        self._move_errors: list[tuple[str, str]] = []

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(24, 24, 24, 24)

        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack)

        # Build both pages
        self._progress_page = self._build_progress_page()
        self._complete_page = self._build_complete_page()

        self._stack.addWidget(self._progress_page)
        self._stack.addWidget(self._complete_page)

        self._stack.setCurrentWidget(self._progress_page)

    # ------------------------------------------------------------------
    # Progress page
    # ------------------------------------------------------------------

    def _build_progress_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("Organizing Your Files...")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(8)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(24)
        layout.addWidget(self._progress_bar)

        # Current file label
        self._current_file_label = QLabel("Moving: ...")
        self._current_file_label.setStyleSheet("color: grey;")
        self._current_file_label.setWordWrap(True)
        layout.addWidget(self._current_file_label)

        # Destination label
        self._dest_label = QLabel("To: ...")
        self._dest_label.setStyleSheet("color: grey;")
        layout.addWidget(self._dest_label)

        # Counter label
        self._counter_label = QLabel("0 of 0 files processed")
        counter_font = QFont()
        counter_font.setBold(True)
        self._counter_label.setFont(counter_font)
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._counter_label)

        layout.addStretch()

        # Please wait label
        wait_label = QLabel("Please wait...")
        wait_font = QFont()
        wait_font.setPointSize(9)
        wait_label.setFont(wait_font)
        wait_label.setStyleSheet("color: grey;")
        wait_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(wait_label)

        return page

    # ------------------------------------------------------------------
    # Complete page
    # ------------------------------------------------------------------

    def _build_complete_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Success header
        success_label = QLabel("\u2705 Success!")
        success_font = QFont()
        success_font.setPointSize(24)
        success_font.setBold(True)
        success_label.setFont(success_font)
        success_label.setStyleSheet("color: #16a34a;")
        success_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(success_label)

        subtitle = QLabel("Your files have been organized!")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle.setFont(subtitle_font)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Stats panel inside a scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._stats_card = QFrame()
        self._stats_card.setProperty("class", "stats-card")
        self._stats_layout = QVBoxLayout(self._stats_card)
        self._stats_layout.setSpacing(8)
        self._stats_layout.setContentsMargins(20, 16, 20, 16)

        scroll.setWidget(self._stats_card)
        layout.addWidget(scroll, 1)

        # Bottom bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self._open_folder_btn = QPushButton("Open Folder")
        self._open_folder_btn.setProperty("class", "primary")
        self._open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_folder_btn.clicked.connect(self._on_open_folder)
        bottom_bar.addWidget(self._open_folder_btn)

        self._undo_btn = QPushButton("Undo")
        self._undo_btn.setProperty("class", "secondary")
        self._undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._undo_btn.clicked.connect(self._on_undo)
        bottom_bar.addWidget(self._undo_btn)

        self._start_over_btn = QPushButton("Organize Another Folder")
        self._start_over_btn.setProperty("class", "secondary")
        self._start_over_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_over_btn.clicked.connect(self._on_start_over)
        bottom_bar.addWidget(self._start_over_btn)

        bottom_bar.addStretch()
        layout.addLayout(bottom_bar)

        return page

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_moving(
        self, source_dir: Path, categories: dict[str, list[FileInfo]]
    ) -> None:
        """Switch to the progress state and start the MoveWorker."""
        self._source_dir = source_dir
        self._categories = categories
        self._completed_moves = []
        self._move_errors = []

        # Reset progress UI
        self._progress_bar.setValue(0)
        self._current_file_label.setText("Moving: ...")
        self._dest_label.setText("To: ...")
        self._counter_label.setText("0 of 0 files processed")

        self._stack.setCurrentWidget(self._progress_page)

        self._move_worker = ProgressScreen.MoveWorker(source_dir, categories)
        self._move_worker.progress.connect(self._on_move_progress)
        self._move_worker.finished.connect(self._on_move_complete)
        self._move_worker.error.connect(self._on_move_error)
        self._move_worker.start()

    def reset(self) -> None:
        """Reset all state for a fresh start."""
        if self._move_worker and self._move_worker.isRunning():
            self._move_worker.quit()
            self._move_worker.wait(3000)
        self._move_worker = None

        if self._undo_worker and self._undo_worker.isRunning():
            self._undo_worker.quit()
            self._undo_worker.wait(3000)
        self._undo_worker = None

        self._source_dir = None
        self._categories = {}
        self._completed_moves = []
        self._move_errors = []

        self._progress_bar.setValue(0)
        self._current_file_label.setText("Moving: ...")
        self._dest_label.setText("To: ...")
        self._counter_label.setText("0 of 0 files processed")

        # Clear stats layout
        self._clear_stats()

        self._stack.setCurrentWidget(self._progress_page)

    # ------------------------------------------------------------------
    # Move slots
    # ------------------------------------------------------------------

    def _on_move_progress(self, current: int, total: int, filename: str) -> None:
        """Update progress bar and labels as files are moved."""
        percent = int((current / total) * 100) if total > 0 else 0
        self._progress_bar.setValue(percent)
        self._current_file_label.setText(f"Moving: {filename}")

        # Determine which category folder the file belongs to
        dest_folder = ""
        for category, files in self._categories.items():
            for fi in files:
                if fi.name == filename:
                    dest_folder = category
                    break
            if dest_folder:
                break
        self._dest_label.setText(f"To: {dest_folder}/")
        self._counter_label.setText(f"{current} of {total} files processed")

    def _on_move_complete(
        self, moves: list[tuple[Path, Path]], errors: list[tuple[str, str]]
    ) -> None:
        """Save to UndoManager, switch to complete state, build summary."""
        self._move_worker = None
        self._completed_moves = moves
        self._move_errors = errors

        # Save to undo history
        if moves:
            undo_mgr = UndoManager()
            undo_mgr.save_operation(
                moves, str(self._source_dir) if self._source_dir else ""
            )

        # Build summary and switch view
        self._build_summary()
        self._stack.setCurrentWidget(self._complete_page)
        self.completed.emit()

    def _on_move_error(self, msg: str) -> None:
        """Show a critical error message box."""
        self._move_worker = None
        QMessageBox.critical(
            self,
            "Error",
            f"An error occurred while organizing files:\n\n{msg}",
        )

    # ------------------------------------------------------------------
    # Summary builder
    # ------------------------------------------------------------------

    def _build_summary(self) -> None:
        """Populate the stats card with move results."""
        self._clear_stats()

        # Summary title
        summary_title = QLabel("Summary")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        summary_title.setFont(title_font)
        self._stats_layout.addWidget(summary_title)

        # Total files moved
        total_label = QLabel(f"Total files moved: {len(self._completed_moves)}")
        total_font = QFont()
        total_font.setPointSize(11)
        total_label.setFont(total_font)
        self._stats_layout.addWidget(total_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        self._stats_layout.addWidget(sep)

        # Count files per category folder
        folder_counts: dict[str, int] = {}
        for category, files in self._categories.items():
            folder_counts[category] = len(files)

        for folder_name, count in sorted(
            folder_counts.items(), key=lambda x: x[1], reverse=True
        ):
            icon = get_category_icon(folder_name)
            label = QLabel(
                f"{icon} {folder_name}: {count} file{'s' if count != 1 else ''}"
            )
            label_font = QFont()
            label_font.setPointSize(11)
            label.setFont(label_font)
            self._stats_layout.addWidget(label)

        # Error summary
        if self._move_errors:
            error_sep = QFrame()
            error_sep.setFrameShape(QFrame.Shape.HLine)
            error_sep.setFrameShadow(QFrame.Shadow.Sunken)
            self._stats_layout.addWidget(error_sep)

            error_count = len(self._move_errors)
            error_label = QLabel(
                f"\u26a0 {error_count} file{'s' if error_count != 1 else ''} "
                f"could not be moved"
            )
            error_label.setStyleSheet("color: #ea580c;")
            error_font = QFont()
            error_font.setPointSize(11)
            error_label.setFont(error_font)
            self._stats_layout.addWidget(error_label)

        self._stats_layout.addStretch()

    def _clear_stats(self) -> None:
        """Remove all widgets from the stats layout."""
        while self._stats_layout.count() > 0:
            item = self._stats_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # ------------------------------------------------------------------
    # Button slots
    # ------------------------------------------------------------------

    def _on_open_folder(self) -> None:
        """Open the source directory in the system file manager."""
        if self._source_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._source_dir)))

    def _on_undo(self) -> None:
        """Show confirmation dialog, then start UndoWorker."""
        reply = QMessageBox.question(
            self,
            "Undo Organization",
            "This will move all files back to their original locations.\n\n"
            "Are you sure you want to undo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._undo_btn.setEnabled(False)
        self._undo_btn.setText("Undoing...")

        self._undo_worker = ProgressScreen.UndoWorker()
        self._undo_worker.finished.connect(self._on_undo_complete)
        self._undo_worker.error.connect(self._on_undo_error)
        self._undo_worker.start()

    def _on_undo_complete(self, succeeded: int, failed: int) -> None:
        """Show result message box after undo completes."""
        self._undo_worker = None
        self._undo_btn.setEnabled(True)
        self._undo_btn.setText("Undo")

        if failed == 0:
            QMessageBox.information(
                self,
                "Undo Complete",
                f"Successfully restored {succeeded} file{'s' if succeeded != 1 else ''} "
                f"to their original locations.",
            )
        else:
            QMessageBox.warning(
                self,
                "Undo Partially Complete",
                f"Restored {succeeded} file{'s' if succeeded != 1 else ''}, "
                f"but {failed} file{'s' if failed != 1 else ''} could not be moved back.",
            )

        self.undo_completed.emit()

    def _on_undo_error(self, msg: str) -> None:
        """Show error if undo fails entirely."""
        self._undo_worker = None
        self._undo_btn.setEnabled(True)
        self._undo_btn.setText("Undo")

        QMessageBox.critical(
            self,
            "Undo Error",
            f"An error occurred while undoing:\n\n{msg}",
        )

    def _on_start_over(self) -> None:
        """Emit signal to restart the organization flow."""
        self.start_over_requested.emit()
