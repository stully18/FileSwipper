"""Screen 2: AI-generated folder suggestions with editable category cards."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QProgressBar,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, QThread, Qt
from PyQt6.QtGui import QFont

from core import FileInfo, CategorySuggestion
from core.ai_suggester import AISuggester, AIError
from utils.file_icons import get_icon, get_category_icon
from utils.validators import validate_folder_name
from gui.dialogs import EditFolderDialog, AddFolderDialog


class CategoryCard(QFrame):
    """A card widget representing one folder suggestion."""

    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    files_changed = pyqtSignal()

    def __init__(self, suggestion: CategorySuggestion, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self._expanded = False
        self._folder_name = suggestion.folder_name
        self._description = suggestion.description
        self._files: list[FileInfo] = list(suggestion.files)

        self._setup_ui()
        self._populate()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)

        # --- Header row ---
        header = QHBoxLayout()
        header.setSpacing(8)

        self._icon_label = QLabel()
        self._icon_label.setFixedWidth(28)
        font = QFont()
        font.setPointSize(16)
        self._icon_label.setFont(font)
        header.addWidget(self._icon_label)

        self._name_label = QLabel()
        name_font = QFont()
        name_font.setPointSize(14)
        name_font.setBold(True)
        self._name_label.setFont(name_font)
        self._name_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        header.addWidget(self._name_label)

        self._edit_btn = QPushButton("\u270f")
        self._edit_btn.setProperty("class", "icon-btn")
        self._edit_btn.setToolTip("Edit folder name")
        self._edit_btn.setFixedSize(32, 32)
        self._edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_btn.clicked.connect(
            lambda: self.edit_requested.emit(self._folder_name)
        )
        header.addWidget(self._edit_btn)

        self._delete_btn = QPushButton("\u2715")
        self._delete_btn.setProperty("class", "icon-btn")
        self._delete_btn.setToolTip("Remove this folder")
        self._delete_btn.setFixedSize(32, 32)
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.clicked.connect(
            lambda: self.delete_requested.emit(self._folder_name)
        )
        header.addWidget(self._delete_btn)

        layout.addLayout(header)

        # --- Description ---
        self._desc_label = QLabel()
        self._desc_label.setProperty("class", "description")
        self._desc_label.setWordWrap(True)
        layout.addWidget(self._desc_label)

        # --- File count badge + toggle row ---
        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        self._count_label = QLabel()
        self._count_label.setStyleSheet(
            "background-color: #dbeafe; color: #1e40af; "
            "border-radius: 10px; padding: 2px 10px; font-size: 10pt; "
            "font-weight: bold;"
        )
        info_row.addWidget(self._count_label)

        info_row.addStretch()

        self._toggle_btn = QPushButton("\u25b6 Show files")
        self._toggle_btn.setProperty("class", "icon-btn")
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle_file_list)
        info_row.addWidget(self._toggle_btn)

        layout.addLayout(info_row)

        # --- File list (hidden by default) ---
        self._file_list = QListWidget()
        self._file_list.setVisible(False)
        self._file_list.setMaximumHeight(200)
        self._file_list.setAlternatingRowColors(False)
        self._file_list.setStyleSheet(
            "QListWidget { background-color: #ffffff; color: #111111; }"
            "QListWidget::item { background-color: #ffffff; color: #111111; }"
        )
        layout.addWidget(self._file_list)

    def _populate(self):
        """Fill in the display data from current state."""
        self._icon_label.setText(get_category_icon(self._folder_name))
        self._name_label.setText(self._folder_name)
        self._desc_label.setText(self._description)

        count = len(self._files)
        self._count_label.setText(
            f"{count} file{'s' if count != 1 else ''}"
        )

        self._file_list.clear()
        for fi in self._files:
            icon = get_icon(fi.extension)
            item = QListWidgetItem(f"{icon}  {fi.name}")
            self._file_list.addItem(item)

    def update_data(self, name: str, description: str, files: list[FileInfo]):
        """Update card display with new data."""
        self._folder_name = name
        self._description = description
        self._files = list(files)
        self._populate()
        self.files_changed.emit()

    def _toggle_file_list(self):
        """Show or hide the file list."""
        self._expanded = not self._expanded
        self._file_list.setVisible(self._expanded)
        if self._expanded:
            self._toggle_btn.setText("\u25bc Hide files")
        else:
            self._toggle_btn.setText("\u25b6 Show files")

    def get_data(self) -> CategorySuggestion:
        """Return current state as a CategorySuggestion."""
        return CategorySuggestion(
            folder_name=self._folder_name,
            description=self._description,
            files=list(self._files),
        )


class SuggestionsScreen(QWidget):
    """Screen 2: displays AI folder suggestions as editable cards."""

    suggestions_accepted = pyqtSignal(dict)
    back_requested = pyqtSignal()

    # --- Inner worker thread ---
    class AIWorker(QThread):
        """Runs AI suggestion in a background thread."""

        finished = pyqtSignal(list)
        error = pyqtSignal(str, str)

        def __init__(self, files: list[FileInfo], api_key: str, model: str):
            super().__init__()
            self._files = files
            self._api_key = api_key
            self._model = model

        def run(self):
            try:
                suggester = AISuggester(api_key=self._api_key, model=self._model)
                # Send a sample of filenames for context + full extension counts
                sample = self._files[:200] if len(self._files) > 200 else self._files
                ext_counts: dict[str, int] = {}
                for f in self._files:
                    ext = f.extension.lower() if f.extension else "(no ext)"
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1

                summary_lines = [f"Total files: {len(self._files)}", "", "Extension counts:"]
                for ext, count in sorted(ext_counts.items(), key=lambda x: x[1], reverse=True):
                    summary_lines.append(f"  {ext}: {count} files")
                summary_lines += ["", f"Sample filenames ({len(sample)} of {len(self._files)}):"]
                for f in sample:
                    summary_lines.append(f"  {f.name}")
                file_summary = "\n".join(summary_lines)

                suggestions = suggester.suggest_categories(file_summary, self._files)
                self.finished.emit(suggestions)
            except AIError as e:
                self.error.emit(e.user_message, str(e))
            except Exception as e:
                self.error.emit(
                    "An unexpected error occurred while analyzing files.",
                    str(e),
                )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: list[FileInfo] = []
        self._api_key = ""
        self._model = "gpt-4o-mini"
        self._cards: list[CategoryCard] = []
        self._worker: SuggestionsScreen.AIWorker | None = None

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # --- Title ---
        title = QLabel("\U0001f916 Suggested Folder Organization")
        title.setProperty("class", "title")
        main_layout.addWidget(title)

        # --- Subtitle ---
        subtitle = QLabel("Review, edit, or add folders before organizing")
        subtitle.setProperty("class", "subtitle")
        main_layout.addWidget(subtitle)

        main_layout.addSpacing(8)

        # --- Loading widget ---
        self._loading_widget = QWidget()
        loading_layout = QVBoxLayout(self._loading_widget)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.setSpacing(16)
        loading_layout.setContentsMargins(40, 40, 40, 40)

        loading_label = QLabel("\U0001f9e0 Analyzing your files with AI...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_font = QFont()
        loading_font.setPointSize(13)
        loading_label.setFont(loading_font)
        loading_layout.addWidget(loading_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indeterminate / busy mode
        self._progress_bar.setFixedHeight(24)
        self._progress_bar.setMaximumWidth(400)
        loading_layout.addWidget(
            self._progress_bar, alignment=Qt.AlignmentFlag.AlignCenter
        )

        self._loading_widget.setVisible(False)
        main_layout.addWidget(self._loading_widget)

        # --- Error widget ---
        self._error_widget = QWidget()
        error_layout = QVBoxLayout(self._error_widget)
        error_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.setSpacing(12)
        error_layout.setContentsMargins(40, 24, 40, 24)

        self._error_label = QLabel()
        self._error_label.setProperty("class", "error")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        error_font = QFont()
        error_font.setPointSize(11)
        self._error_label.setFont(error_font)
        error_layout.addWidget(self._error_label)

        self._error_detail_label = QLabel()
        self._error_detail_label.setProperty("class", "description")
        self._error_detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_detail_label.setWordWrap(True)
        error_layout.addWidget(self._error_detail_label)

        error_btn_row = QHBoxLayout()
        error_btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_btn_row.setSpacing(12)

        retry_btn = QPushButton("Try Again")
        retry_btn.setProperty("class", "secondary")
        retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        retry_btn.clicked.connect(self._on_regenerate)
        error_btn_row.addWidget(retry_btn)

        fallback_btn = QPushButton("Use Basic Sorting")
        fallback_btn.setProperty("class", "secondary")
        fallback_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fallback_btn.clicked.connect(self._on_use_fallback)
        error_btn_row.addWidget(fallback_btn)

        error_layout.addLayout(error_btn_row)

        self._error_widget.setVisible(False)
        main_layout.addWidget(self._error_widget)

        # --- Scroll area for cards ---
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setSpacing(12)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.addStretch()

        self._scroll_area.setWidget(self._cards_container)
        self._scroll_area.setVisible(False)
        main_layout.addWidget(self._scroll_area, 1)

        # --- Bottom bar ---
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self._add_btn = QPushButton("+ Add Folder")
        self._add_btn.setProperty("class", "secondary")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._on_add_folder)
        bottom_bar.addWidget(self._add_btn)

        self._regen_btn = QPushButton("\u21bb Regenerate")
        self._regen_btn.setProperty("class", "secondary")
        self._regen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._regen_btn.clicked.connect(self._on_regenerate)
        bottom_bar.addWidget(self._regen_btn)

        bottom_bar.addStretch()

        self._back_btn = QPushButton("Back")
        self._back_btn.setProperty("class", "secondary")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self.back_requested.emit)
        bottom_bar.addWidget(self._back_btn)

        self._next_btn = QPushButton("Next: Preview")
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(self._on_accept)
        bottom_bar.addWidget(self._next_btn)

        self._bottom_widget = QWidget()
        self._bottom_widget.setLayout(bottom_bar)
        self._bottom_widget.setVisible(False)
        main_layout.addWidget(self._bottom_widget)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_suggestions(
        self,
        files: list[FileInfo],
        api_key: str,
        model: str = "gpt-4o-mini",
    ):
        """Store files, show loading indicator, and start the AI worker."""
        self._files = files
        self._api_key = api_key
        self._model = model

        self._show_loading()

        self._worker = SuggestionsScreen.AIWorker(files, api_key, model)
        self._worker.finished.connect(self._on_ai_complete)
        self._worker.error.connect(self._on_ai_error)
        self._worker.start()

    def reset(self):
        """Clear everything for a fresh start."""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(3000)
        self._worker = None
        self._files = []
        self._cards.clear()
        self._clear_cards_layout()
        self._loading_widget.setVisible(False)
        self._error_widget.setVisible(False)
        self._scroll_area.setVisible(False)
        self._bottom_widget.setVisible(False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _show_loading(self):
        self._loading_widget.setVisible(True)
        self._error_widget.setVisible(False)
        self._scroll_area.setVisible(False)
        self._bottom_widget.setVisible(False)

    def _show_results(self):
        self._loading_widget.setVisible(False)
        self._error_widget.setVisible(False)
        self._scroll_area.setVisible(True)
        self._bottom_widget.setVisible(True)

    def _show_error(self):
        self._loading_widget.setVisible(False)
        self._error_widget.setVisible(True)
        self._scroll_area.setVisible(False)
        self._bottom_widget.setVisible(False)

    def _clear_cards_layout(self):
        """Remove all cards from the scroll area layout."""
        while self._cards_layout.count() > 0:
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _build_cards(self, suggestions: list[CategorySuggestion]):
        """Clear scroll area and create a CategoryCard for each suggestion."""
        self._cards.clear()
        self._clear_cards_layout()

        for suggestion in suggestions:
            card = CategoryCard(suggestion)
            card.edit_requested.connect(self._on_edit_category)
            card.delete_requested.connect(self._on_delete_category)
            self._cards.append(card)
            self._cards_layout.insertWidget(self._cards_layout.count() - 0, card)

        # Trailing stretch to push cards to the top
        self._cards_layout.addStretch()

    def _find_card(self, category_name: str) -> CategoryCard | None:
        """Find a card by its current folder name."""
        for card in self._cards:
            if card._folder_name == category_name:
                return card
        return None

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_ai_complete(self, suggestions: list[CategorySuggestion]):
        """Hide loading, create cards, show results."""
        self._worker = None
        self._build_cards(suggestions)
        self._show_results()

    def _on_ai_error(self, user_msg: str, detail: str):
        """Hide loading, show error widget with message."""
        self._worker = None
        self._error_label.setText(user_msg)
        self._error_detail_label.setText(detail)
        self._show_error()

    def _on_use_fallback(self):
        """Use extension-based fallback categories instead of AI."""
        suggestions = AISuggester.fallback_categories(self._files)
        self._build_cards(suggestions)
        self._show_results()

    def _on_regenerate(self):
        """Clear cards and re-call the AI."""
        self._cards.clear()
        self._clear_cards_layout()
        self.load_suggestions(self._files, self._api_key, self._model)

    def _on_edit_category(self, category_name: str):
        """Open EditFolderDialog and update the card."""
        card = self._find_card(category_name)
        if card is None:
            return

        dialog = EditFolderDialog(
            current_name=card._folder_name,
            current_description=card._description,
            parent=self,
        )

        if dialog.exec():
            card.update_data(dialog.folder_name, dialog.description, card._files)

    def _on_delete_category(self, category_name: str):
        """Remove card and move its files to the 'Other' card (create if needed)."""
        card = self._find_card(category_name)
        if card is None:
            return

        orphaned_files = list(card._files)

        # Remove the card
        self._cards.remove(card)
        card.deleteLater()

        if not orphaned_files:
            return

        # Find or create an "Other" card
        other_card = self._find_card("Other")
        if other_card is None:
            other_suggestion = CategorySuggestion(
                folder_name="Other",
                description="Miscellaneous files",
                files=orphaned_files,
            )
            other_card = CategoryCard(other_suggestion)
            other_card.edit_requested.connect(self._on_edit_category)
            other_card.delete_requested.connect(self._on_delete_category)
            self._cards.append(other_card)
            # Insert before the trailing stretch
            self._cards_layout.insertWidget(
                max(self._cards_layout.count() - 1, 0), other_card
            )
        else:
            merged = other_card._files + orphaned_files
            other_card.update_data(
                other_card._folder_name,
                other_card._description,
                merged,
            )

    def _on_add_folder(self):
        """Open AddFolderDialog and create a new empty CategoryCard."""
        dialog = AddFolderDialog(parent=self)

        if dialog.exec():
            name = dialog.folder_name
            description = dialog.description
            suggestion = CategorySuggestion(
                folder_name=name,
                description=description,
                files=[],
            )
            card = CategoryCard(suggestion)
            card.edit_requested.connect(self._on_edit_category)
            card.delete_requested.connect(self._on_delete_category)
            self._cards.append(card)
            self._cards_layout.insertWidget(
                max(self._cards_layout.count() - 1, 0), card
            )

    def _on_accept(self):
        """Collect all cards' data, check for duplicates, emit signal."""
        # Check for duplicate folder names
        names = [card._folder_name for card in self._cards]
        seen: set[str] = set()
        duplicates: set[str] = set()
        for name in names:
            if name in seen:
                duplicates.add(name)
            seen.add(name)

        if duplicates:
            dup_list = ", ".join(sorted(duplicates))
            QMessageBox.warning(
                self,
                "Duplicate Folder Names",
                f"The following folder names are used more than once:\n\n"
                f"{dup_list}\n\n"
                f"Please rename or remove duplicate folders before continuing.",
            )
            return

        # Build result dict: {folder_name: [FileInfo]}
        result: dict[str, list[FileInfo]] = {}
        for card in self._cards:
            data = card.get_data()
            if data.files:  # skip empty folders
                result[data.folder_name] = data.files

        self.suggestions_accepted.emit(result)
