from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import FileInfo
from core.analyzer import DirectoryAnalyzer
from utils.file_icons import get_category_icon


class FolderSelectionScreen(QWidget):
    """Screen 1 -- lets the user pick a folder, scan it, and view file stats."""

    analysis_complete = pyqtSignal(list)

    # ------------------------------------------------------------------
    # Inner worker thread
    # ------------------------------------------------------------------
    class ScanWorker(QThread):
        progress = pyqtSignal(int, int)
        finished = pyqtSignal(list)
        error = pyqtSignal(str)

        def __init__(self, path: Path, parent=None):
            super().__init__(parent)
            self._path = path

        def run(self):
            try:
                analyzer = DirectoryAnalyzer(self._path)
                files = analyzer.scan(
                    progress_callback=lambda current, total: self.progress.emit(
                        current, total
                    )
                )
                self.finished.emit(files)
            except Exception as exc:
                self.error.emit(str(exc))

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_path: Path | None = None
        self._files: list[FileInfo] = []
        self._worker: FolderSelectionScreen.ScanWorker | None = None
        self._category_labels: list[QLabel] = []
        self._init_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 1. Title
        self._title_label = QLabel("Select a Folder to Organize")
        self._title_label.setProperty("class", "title")
        font = self._title_label.font()
        font.setPointSize(18)
        font.setBold(True)
        self._title_label.setFont(font)
        self._title_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        layout.addWidget(self._title_label)

        # 2. Subtitle
        self._subtitle_label = QLabel(
            "Choose a folder and we'll analyze its contents"
        )
        self._subtitle_label.setProperty("class", "subtitle")
        self._subtitle_label.setStyleSheet("color: grey; font-size: 12pt;")
        layout.addWidget(self._subtitle_label)

        # 3. Spacer
        layout.addSpacing(20)

        # 4. Folder path row
        path_row = QHBoxLayout()
        self._path_input = QLineEdit()
        self._path_input.setReadOnly(True)
        self._path_input.setPlaceholderText("\U0001f4c2 No folder selected")
        path_row.addWidget(self._path_input, stretch=1)

        self._browse_button = QPushButton("Browse")
        self._browse_button.clicked.connect(self._on_browse_clicked)
        path_row.addWidget(self._browse_button)

        layout.addLayout(path_row)

        # 5. Analyze button
        self._analyze_button = QPushButton("Analyze Files")
        self._analyze_button.setEnabled(False)
        self._analyze_button.setProperty("class", "primary")
        self._analyze_button.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; "
            "padding: 8px 24px; border-radius: 4px; font-size: 11pt; }"
            "QPushButton:disabled { background-color: #90CAF9; }"
        )
        self._analyze_button.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self._analyze_button)

        # 6. Progress bar (hidden)
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        # 7. Status label (hidden)
        self._status_label = QLabel()
        self._status_label.setVisible(False)
        self._status_label.setProperty("class", "status")
        layout.addWidget(self._status_label)

        # 8. Stats panel (hidden)
        self._stats_frame = QFrame()
        self._stats_frame.setProperty("class", "stats-card")
        self._stats_frame.setStyleSheet(
            "QFrame[class='stats-card'] { background-color: white; "
            "border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; }"
        )
        self._stats_frame.setVisible(False)

        stats_layout = QVBoxLayout(self._stats_frame)
        stats_layout.setSpacing(8)

        self._stats_title = QLabel("\U0001f4ca Analysis Results")
        stats_title_font = self._stats_title.font()
        stats_title_font.setPointSize(14)
        stats_title_font.setBold(True)
        self._stats_title.setFont(stats_title_font)
        stats_layout.addWidget(self._stats_title)

        self._total_label = QLabel()
        total_font = self._total_label.font()
        total_font.setBold(True)
        self._total_label.setFont(total_font)
        stats_layout.addWidget(self._total_label)

        self._separator = QFrame()
        self._separator.setFrameShape(QFrame.Shape.HLine)
        self._separator.setFrameShadow(QFrame.Shadow.Sunken)
        stats_layout.addWidget(self._separator)

        # Container for dynamic category labels
        self._categories_layout = QVBoxLayout()
        self._categories_layout.setSpacing(4)
        stats_layout.addLayout(self._categories_layout)

        layout.addWidget(self._stats_frame)

        # 9. Continue button (hidden)
        self._continue_button = QPushButton("Continue")
        self._continue_button.setProperty("class", "success")
        self._continue_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 8px 24px; border-radius: 4px; font-size: 11pt; }"
        )
        self._continue_button.setVisible(False)
        self._continue_button.clicked.connect(self._on_continue_clicked)
        layout.addWidget(self._continue_button)

        # Push everything toward the top
        layout.addStretch()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_browse_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self._selected_path = Path(folder)
            self._path_input.setText(f"\U0001f4c2 {folder}")
            self._analyze_button.setEnabled(True)

    def _on_analyze_clicked(self):
        if self._selected_path is None:
            return

        self._analyze_button.setEnabled(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._status_label.setText("Starting scan\u2026")
        self._status_label.setVisible(True)
        self._stats_frame.setVisible(False)
        self._continue_button.setVisible(False)

        self._worker = FolderSelectionScreen.ScanWorker(self._selected_path, self)
        self._worker.progress.connect(self._on_scan_progress)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.error.connect(self._on_scan_error)
        self._worker.start()

    def _on_scan_progress(self, current: int, total: int):
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current)
        self._status_label.setText(f"Scanning {current} of {total} files\u2026")

    def _on_scan_finished(self, files: list):
        self._files = files
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"Scan complete \u2014 {len(files)} files found.")

        # Build stats display
        analyzer = DirectoryAnalyzer(self._selected_path)
        summary = analyzer.get_type_summary(files)

        self._total_label.setText(f"Total files: {len(files)}")

        # Clear old category labels
        for lbl in self._category_labels:
            self._categories_layout.removeWidget(lbl)
            lbl.deleteLater()
        self._category_labels.clear()

        for category, count in sorted(summary.items(), key=lambda x: -x[1]):
            icon = get_category_icon(category)
            lbl = QLabel(f"{icon} {category}: {count} files")
            self._categories_layout.addWidget(lbl)
            self._category_labels.append(lbl)

        self._stats_frame.setVisible(True)
        self._continue_button.setVisible(True)
        self._analyze_button.setEnabled(True)

    def _on_scan_error(self, msg: str):
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"Error: {msg}")
        self._status_label.setStyleSheet("color: red;")
        self._analyze_button.setEnabled(True)

    def _on_continue_clicked(self):
        self.analysis_complete.emit(self._files)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def reset(self):
        """Reset all UI elements to initial state."""
        self._selected_path = None
        self._files = []
        self._path_input.clear()
        self._path_input.setPlaceholderText("\U0001f4c2 No folder selected")
        self._analyze_button.setEnabled(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self._status_label.setText("")
        self._status_label.setVisible(False)
        self._status_label.setStyleSheet("")
        self._stats_frame.setVisible(False)
        self._continue_button.setVisible(False)

        for lbl in self._category_labels:
            self._categories_layout.removeWidget(lbl)
            lbl.deleteLater()
        self._category_labels.clear()
