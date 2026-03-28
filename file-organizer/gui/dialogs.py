"""Dialog windows for the AI File Organizer application."""

import openai
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from core.undo_manager import UndoManager
from utils.validators import validate_folder_name

SETTINGS_ORG = "AIFileOrganizer"
SETTINGS_APP = "AIFileOrganizer"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_api_key_row():
    """Create an API key input with a show/hide toggle button.

    Returns (layout, line_edit, toggle_button).
    """
    layout = QHBoxLayout()
    line_edit = QLineEdit()
    line_edit.setEchoMode(QLineEdit.EchoMode.Password)
    line_edit.setPlaceholderText("sk-...")

    toggle_btn = QPushButton("Show")
    toggle_btn.setFixedWidth(60)
    toggle_btn.setCheckable(True)

    def _toggle(checked: bool):
        if checked:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            toggle_btn.setText("Hide")
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            toggle_btn.setText("Show")

    toggle_btn.toggled.connect(_toggle)

    layout.addWidget(line_edit)
    layout.addWidget(toggle_btn)
    return layout, line_edit, toggle_btn


def _test_api_key(api_key: str) -> tuple[bool, str]:
    """Test an OpenAI API key by listing models. Returns (success, message)."""
    try:
        client = openai.OpenAI(api_key=api_key)
        client.models.list()
        return True, "Connection successful!"
    except openai.AuthenticationError:
        return False, "Invalid API key."
    except (openai.APIConnectionError, openai.APITimeoutError):
        return False, "Could not connect to OpenAI. Check your internet connection."
    except openai.OpenAIError as exc:
        return False, f"API error: {exc}"


# ---------------------------------------------------------------------------
# 1. FirstTimeSetupDialog
# ---------------------------------------------------------------------------

class FirstTimeSetupDialog(QDialog):
    """Shown on first launch to collect the OpenAI API key."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("First-Time Setup")
        self.setMinimumWidth(500)
        self._build_ui()

    # -- UI ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 28, 32, 24)

        # Welcome heading
        title = QLabel("Welcome to AI File Organizer!")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Let's get you set up.")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Explanation
        explanation = QLabel(
            "AI File Organizer uses OpenAI to intelligently suggest how to "
            "organize your files into folders. To get started, you'll need an "
            "OpenAI API key. Your key is stored locally and is never shared."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        layout.addSpacing(4)

        # API key
        key_label = QLabel("OpenAI API Key")
        key_label.setFont(QFont())
        layout.addWidget(key_label)

        key_row, self._key_edit, self._toggle_btn = _create_api_key_row()
        layout.addLayout(key_row)

        instructions = QLabel("You can get an API key from OpenAI's website.")
        instructions.setStyleSheet("color: grey; font-size: 11px;")
        layout.addWidget(instructions)

        layout.addSpacing(4)

        # Status label (for test results)
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # Test Connection button
        self._test_btn = QPushButton("Test Connection")
        self._test_btn.clicked.connect(self._on_test_connection)
        layout.addWidget(self._test_btn)

        layout.addSpacing(12)

        # Save & Continue
        self._save_btn = QPushButton("Save && Continue")
        self._save_btn.setEnabled(False)
        self._save_btn.setDefault(True)
        self._save_btn.clicked.connect(self._on_save)
        layout.addWidget(self._save_btn)

        # Enable save button when text is entered
        self._key_edit.textChanged.connect(self._on_key_changed)

    # -- Slots ---------------------------------------------------------------

    def _on_key_changed(self, text: str):
        self._save_btn.setEnabled(bool(text.strip()))
        self._status_label.setText("")

    def _on_test_connection(self):
        key = self._key_edit.text().strip()
        if not key:
            self._status_label.setStyleSheet("color: red;")
            self._status_label.setText("Please enter an API key first.")
            return

        self._test_btn.setEnabled(False)
        self._test_btn.setText("Testing...")
        # Process events so the button text updates
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        success, message = _test_api_key(key)

        self._test_btn.setEnabled(True)
        self._test_btn.setText("Test Connection")

        if success:
            self._status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self._status_label.setStyleSheet("color: red;")
        self._status_label.setText(message)

    def _on_save(self):
        key = self._key_edit.text().strip()
        if not key:
            return
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        settings.setValue("api_key", key)
        self.accept()


# ---------------------------------------------------------------------------
# 2. SettingsDialog
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self._build_ui()
        self._load_settings()

    # -- UI ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 20, 24, 20)

        heading = QLabel("Settings")
        heading_font = QFont()
        heading_font.setPointSize(15)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        layout.addWidget(heading)

        layout.addSpacing(4)

        # --- API Key ---------------------------------------------------------
        layout.addWidget(QLabel("OpenAI API Key"))
        key_row, self._key_edit, self._toggle_btn = _create_api_key_row()
        layout.addLayout(key_row)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._test_btn = QPushButton("Test Connection")
        self._test_btn.clicked.connect(self._on_test_connection)
        layout.addWidget(self._test_btn)

        layout.addSpacing(8)

        # --- AI Model --------------------------------------------------------
        layout.addWidget(QLabel("AI Model"))
        self._model_combo = QComboBox()
        self._model_combo.addItem("gpt-4o-mini (Recommended)", "gpt-4o-mini")
        self._model_combo.addItem("gpt-4o (Better, costs more)", "gpt-4o")
        layout.addWidget(self._model_combo)

        layout.addSpacing(4)

        # --- Theme -----------------------------------------------------------
        layout.addWidget(QLabel("Theme"))
        self._theme_combo = QComboBox()
        self._theme_combo.addItem("Light", "light")
        self._theme_combo.addItem("Dark", "dark")
        layout.addWidget(self._theme_combo)

        layout.addSpacing(4)

        # --- Hidden files ----------------------------------------------------
        self._hidden_check = QCheckBox("Include hidden files in scan")
        layout.addWidget(self._hidden_check)

        layout.addSpacing(4)

        # --- Number of suggestions -------------------------------------------
        suggestions_row = QHBoxLayout()
        suggestions_row.addWidget(QLabel("Number of suggestions"))
        self._suggestions_spin = QSpinBox()
        self._suggestions_spin.setMinimum(3)
        self._suggestions_spin.setMaximum(8)
        self._suggestions_spin.setValue(5)
        suggestions_row.addWidget(self._suggestions_spin)
        suggestions_row.addStretch()
        layout.addLayout(suggestions_row)

        layout.addSpacing(8)

        # --- Clear Undo History ----------------------------------------------
        self._clear_undo_btn = QPushButton("Clear Undo History")
        self._clear_undo_btn.setProperty("class", "secondary")
        self._clear_undo_btn.clicked.connect(self._on_clear_undo)
        layout.addWidget(self._clear_undo_btn)

        layout.addSpacing(12)

        # --- OK / Cancel -----------------------------------------------------
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setProperty(
            "class", "secondary"
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    # -- Settings persistence ------------------------------------------------

    def _load_settings(self):
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._key_edit.setText(settings.value("api_key", "", type=str))

        model = settings.value("model", "gpt-4o-mini", type=str)
        idx = self._model_combo.findData(model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)

        theme = settings.value("theme", "light", type=str)
        idx = self._theme_combo.findData(theme)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)

        self._hidden_check.setChecked(
            settings.value("include_hidden", False, type=bool)
        )
        self._suggestions_spin.setValue(
            settings.value("num_suggestions", 5, type=int)
        )

    def _save_settings(self):
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        settings.setValue("api_key", self._key_edit.text().strip())
        settings.setValue("model", self._model_combo.currentData())
        settings.setValue("theme", self._theme_combo.currentData())
        settings.setValue("include_hidden", self._hidden_check.isChecked())
        settings.setValue("num_suggestions", self._suggestions_spin.value())

    # -- Slots ---------------------------------------------------------------

    def _on_test_connection(self):
        key = self._key_edit.text().strip()
        if not key:
            self._status_label.setStyleSheet("color: red;")
            self._status_label.setText("Please enter an API key first.")
            return

        self._test_btn.setEnabled(False)
        self._test_btn.setText("Testing...")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        success, message = _test_api_key(key)

        self._test_btn.setEnabled(True)
        self._test_btn.setText("Test Connection")

        if success:
            self._status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self._status_label.setStyleSheet("color: red;")
        self._status_label.setText(message)

    def _on_clear_undo(self):
        reply = QMessageBox.question(
            self,
            "Clear Undo History",
            "Are you sure you want to clear the entire undo history? "
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            UndoManager().clear_history()
            QMessageBox.information(
                self, "Undo History", "Undo history has been cleared."
            )

    def _on_accept(self):
        self._save_settings()
        self.accept()


# ---------------------------------------------------------------------------
# 3. EditFolderDialog
# ---------------------------------------------------------------------------

class EditFolderDialog(QDialog):
    """Edit an existing folder's name and description."""

    def __init__(self, current_name: str, current_description: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Folder")
        self.setMinimumWidth(420)
        self._build_ui(current_name, current_description)

    # -- UI ------------------------------------------------------------------

    def _build_ui(self, current_name: str, current_description: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 20, 24, 20)

        heading = QLabel("Edit Folder")
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        layout.addWidget(heading)

        layout.addSpacing(4)

        # Folder name
        layout.addWidget(QLabel("Folder Name"))
        self._name_edit = QLineEdit(current_name)
        layout.addWidget(self._name_edit)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red; font-size: 11px;")
        self._error_label.setWordWrap(True)
        layout.addWidget(self._error_label)

        layout.addSpacing(4)

        # Description
        layout.addWidget(QLabel("Description (optional)"))
        self._desc_edit = QTextEdit()
        self._desc_edit.setPlainText(current_description)
        self._desc_edit.setFixedHeight(72)  # ~3 rows
        self._desc_edit.setPlaceholderText("Describe what belongs in this folder...")
        layout.addWidget(self._desc_edit)

        layout.addSpacing(8)

        # OK / Cancel
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setProperty(
            "class", "secondary"
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

        # Real-time validation
        self._name_edit.textChanged.connect(self._validate)
        # Run initial validation
        self._validate()

    # -- Validation ----------------------------------------------------------

    def _validate(self):
        name = self._name_edit.text()
        is_valid, error = validate_folder_name(name)
        self._error_label.setText(error)
        ok_btn = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setEnabled(is_valid)

    # -- Properties ----------------------------------------------------------

    @property
    def folder_name(self) -> str:
        return self._name_edit.text().strip()

    @property
    def description(self) -> str:
        return self._desc_edit.toPlainText().strip()


# ---------------------------------------------------------------------------
# 4. AddFolderDialog
# ---------------------------------------------------------------------------

class AddFolderDialog(QDialog):
    """Add a brand-new custom folder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Custom Folder")
        self.setMinimumWidth(420)
        self._build_ui()

    # -- UI ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 20, 24, 20)

        heading = QLabel("Add Custom Folder")
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        layout.addWidget(heading)

        layout.addSpacing(4)

        # Folder name
        layout.addWidget(QLabel("Folder Name"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Receipts, Work Projects, ...")
        layout.addWidget(self._name_edit)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red; font-size: 11px;")
        self._error_label.setWordWrap(True)
        layout.addWidget(self._error_label)

        layout.addSpacing(4)

        # Description
        layout.addWidget(QLabel("Description (optional)"))
        self._desc_edit = QTextEdit()
        self._desc_edit.setFixedHeight(72)
        self._desc_edit.setPlaceholderText("Describe what belongs in this folder...")
        layout.addWidget(self._desc_edit)

        layout.addSpacing(4)

        # Info label
        info = QLabel("You can assign files to this folder in the suggestions view.")
        info.setStyleSheet("color: grey; font-size: 11px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addSpacing(8)

        # OK / Cancel
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setProperty(
            "class", "secondary"
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

        # Real-time validation
        self._name_edit.textChanged.connect(self._validate)
        # Run initial validation (empty name is invalid, so OK starts disabled)
        self._validate()

    # -- Validation ----------------------------------------------------------

    def _validate(self):
        name = self._name_edit.text()
        is_valid, error = validate_folder_name(name)
        self._error_label.setText(error)
        ok_btn = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setEnabled(is_valid)

    # -- Properties ----------------------------------------------------------

    @property
    def folder_name(self) -> str:
        return self._name_edit.text().strip()

    @property
    def description(self) -> str:
        return self._desc_edit.toPlainText().strip()
