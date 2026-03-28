"""Screen 3: Preview file organization plan before executing moves."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QCheckBox,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from core import FileInfo
from utils.file_icons import get_icon, get_category_icon

MAX_VISIBLE_FILES = 20


class PreviewScreen(QWidget):
    """Preview the organization plan and confirm before moving files."""

    confirmed = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._categories: dict[str, list[FileInfo]] = {}
        self._source_dir: str = ""

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # --- Title ---
        title = QLabel("Preview Organization")
        title.setProperty("class", "title")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # --- Subtitle ---
        subtitle = QLabel("Review the changes before organizing your files")
        subtitle.setProperty("class", "subtitle")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet("color: grey;")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # --- Summary ---
        self._summary_label = QLabel()
        self._summary_label.setProperty("class", "summary")
        summary_font = QFont()
        summary_font.setBold(True)
        self._summary_label.setFont(summary_font)
        layout.addWidget(self._summary_label)

        # --- Tree widget ---
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["File Organization Plan"])
        self._tree.setProperty("class", "preview-tree")
        self._tree.setAlternatingRowColors(True)
        layout.addWidget(self._tree, 1)  # stretch factor 1

        # --- Checkbox ---
        self._dir_checkbox = QCheckBox("Create folders in: ")
        self._dir_checkbox.setChecked(True)
        self._dir_checkbox.setEnabled(False)
        layout.addWidget(self._dir_checkbox)

        # --- Bottom bar ---
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self._back_btn = QPushButton("Back")
        self._back_btn.setProperty("class", "secondary")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self._on_back_clicked)
        bottom_bar.addWidget(self._back_btn)

        bottom_bar.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setProperty("class", "secondary")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        bottom_bar.addWidget(self._cancel_btn)

        self._organize_btn = QPushButton("Organize Files")
        self._organize_btn.setProperty("class", "success")
        self._organize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._organize_btn.setStyleSheet(
            "QPushButton { background-color: #16a34a; color: white; "
            "font-weight: bold; padding: 8px 24px; border-radius: 6px; "
            "font-size: 11pt; }"
            "QPushButton:hover { background-color: #15803d; }"
            "QPushButton:pressed { background-color: #166534; }"
        )
        self._organize_btn.clicked.connect(self._on_organize_clicked)
        bottom_bar.addWidget(self._organize_btn)

        layout.addLayout(bottom_bar)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_preview(
        self, categories: dict[str, list[FileInfo]], source_dir: str
    ):
        """Clear tree and rebuild from the given categories."""
        self._categories = categories
        self._source_dir = source_dir
        self._update_summary()
        self._dir_checkbox.setText(f"Create folders in: {source_dir}")
        self._build_tree()

    def reset(self):
        """Clear the tree and stored data."""
        self._tree.clear()
        self._categories = {}
        self._source_dir = ""
        self._summary_label.setText("")
        self._dir_checkbox.setText("Create folders in: ")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _total_files(self) -> int:
        return sum(len(files) for files in self._categories.values())

    def _total_folders(self) -> int:
        return len(self._categories)

    def _update_summary(self):
        files = self._total_files()
        folders = self._total_folders()
        self._summary_label.setText(
            f"{files} file{'s' if files != 1 else ''} will be moved into "
            f"{folders} folder{'s' if folders != 1 else ''}"
        )

    def _build_tree(self):
        """Populate the QTreeWidget from stored categories."""
        self._tree.clear()

        for folder_name in sorted(self._categories.keys()):
            file_list = self._categories[folder_name]
            count = len(file_list)

            # Top-level folder item
            folder_item = QTreeWidgetItem(self._tree)
            icon = get_category_icon(folder_name)
            folder_item.setText(
                0, f"{icon}  {folder_name} ({count} file{'s' if count != 1 else ''})"
            )
            bold_font = QFont()
            bold_font.setBold(True)
            folder_item.setFont(0, bold_font)

            # Child file items
            visible_files = file_list[:MAX_VISIBLE_FILES]
            for fi in visible_files:
                file_item = QTreeWidgetItem(folder_item)
                file_icon = get_icon(fi.extension)
                file_item.setText(0, f"{file_icon}  {fi.name}")

            # Overflow indicator
            remaining = count - MAX_VISIBLE_FILES
            if remaining > 0:
                more_item = QTreeWidgetItem(folder_item)
                more_item.setText(
                    0, f"... and {remaining} more file{'s' if remaining != 1 else ''}"
                )
                more_item.setDisabled(True)
                italic_font = QFont()
                italic_font.setItalic(True)
                more_item.setFont(0, italic_font)

            # Expand small folders, collapse large ones
            if count <= MAX_VISIBLE_FILES:
                folder_item.setExpanded(True)
            else:
                folder_item.setExpanded(False)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_organize_clicked(self):
        """Show confirmation dialog, emit confirmed if accepted."""
        files = self._total_files()
        folders = self._total_folders()

        reply = QMessageBox.question(
            self,
            "Confirm Organization",
            f"This will move {files} file{'s' if files != 1 else ''} into "
            f"{folders} folder{'s' if folders != 1 else ''}. "
            f"This action can be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.confirmed.emit()

    def _on_back_clicked(self):
        """Emit back_requested signal."""
        self.back_requested.emit()

    def _on_cancel_clicked(self):
        """Show confirmation, reset if accepted."""
        reply = QMessageBox.question(
            self,
            "Cancel Organization",
            "Are you sure you want to cancel? All progress will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.reset()
            # Close the top-level window to end the app flow
            window = self.window()
            if window and window is not self:
                window.close()
