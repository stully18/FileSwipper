"""Entry point for the AI File Organizer application."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AI File Organizer")
    app.setOrganizationName("AIFileOrganizer")

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
