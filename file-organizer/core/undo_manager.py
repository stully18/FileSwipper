"""Undo management for the AI File Organizer."""

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class UndoManager:
    """Tracks file-move operations and supports undoing the most recent one."""

    HISTORY_DIR = Path.home() / ".config" / "ai-file-organizer"
    HISTORY_FILE = HISTORY_DIR / "undo_history.json"

    def save_operation(self, moves: list[tuple[Path, Path]], source_dir: str) -> None:
        """Append an operation to the history file, keeping only the last 10."""
        history = self._load_history()

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_dir": source_dir,
            "moves": [[str(src), str(dest)] for src, dest in moves],
        }
        history.append(entry)

        # Keep only the last 10 operations
        history = history[-10:]
        self._save_history(history)

    def get_last_operation(self) -> dict | None:
        """Return the most recent operation, or None if history is empty."""
        history = self._load_history()
        if not history:
            return None
        return history[-1]

    def undo_last(self, progress_callback=None) -> tuple[int, int]:
        """Reverse the most recent operation by moving files back.

        Args:
            progress_callback: Optional callable(current, total).

        Returns:
            Tuple of (succeeded, failed) counts.
        """
        history = self._load_history()
        if not history:
            return (0, 0)

        operation = history.pop()
        moves = operation["moves"]
        total = len(moves)
        succeeded = 0
        failed = 0

        dirs_to_check: set[Path] = set()

        for current, (src_str, dest_str) in enumerate(moves, start=1):
            src = Path(src_str)
            dest = Path(dest_str)

            try:
                if dest.exists():
                    # Ensure the original parent directory exists
                    src.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(dest), str(src))
                    succeeded += 1
                    dirs_to_check.add(dest.parent)
                else:
                    logger.warning("Destination no longer exists: %s", dest)
                    failed += 1
            except (PermissionError, OSError) as exc:
                logger.warning("Failed to undo move %s -> %s: %s", dest, src, exc)
                failed += 1

            if progress_callback is not None:
                progress_callback(current, total)

        # Remove empty directories left behind
        for dir_path in sorted(dirs_to_check, key=lambda p: len(p.parts), reverse=True):
            try:
                if dir_path.exists() and dir_path.is_dir() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
            except OSError:
                pass

        self._save_history(history)
        return (succeeded, failed)

    def clear_history(self) -> None:
        """Delete the history file."""
        if self.HISTORY_FILE.exists():
            self.HISTORY_FILE.unlink()

    def _load_history(self) -> list[dict]:
        """Load operation history from the JSON file."""
        if not self.HISTORY_FILE.exists():
            return []
        try:
            text = self.HISTORY_FILE.read_text(encoding="utf-8")
            data = json.loads(text)
            if isinstance(data, list):
                return data
            return []
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load undo history: %s", exc)
            return []

    def _save_history(self, history: list[dict]) -> None:
        """Write operation history to the JSON file."""
        self.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        self.HISTORY_FILE.write_text(
            json.dumps(history, indent=2),
            encoding="utf-8",
        )
