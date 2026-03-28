"""Entry point for the AI File Organizer application."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow

SETTINGS_ORG = "AIFileOrganizer"
SETTINGS_APP = "AIFileOrganizer"


def _load_env_key():
    """If a GEMINI_API_KEY exists in .env, write it into QSettings."""
    load_dotenv(Path(__file__).parent / ".env")
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        settings.setValue("api_key", key)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AI File Organizer")
    app.setOrganizationName("AIFileOrganizer")

    _load_env_key()

    # Load stylesheet
    style_path = Path(__file__).parent / "resources" / "styles.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text())

    window = MainWindow()
    window.show()
    window._check_first_run()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
