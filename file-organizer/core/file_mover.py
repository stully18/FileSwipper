"""File moving operations for the AI File Organizer."""

import logging
import shutil
from pathlib import Path

from core import FileInfo

logger = logging.getLogger(__name__)


class FileMover:
    """Handles moving files into categorized subdirectories."""

    def __init__(self, source_dir: Path) -> None:
        self.source_dir = source_dir
        self.completed_moves: list[tuple[Path, Path]] = []
        self.errors: list[tuple[str, str]] = []

    def execute_plan(
        self,
        categories: dict[str, list[FileInfo]],
        progress_callback=None,
    ) -> list[tuple[Path, Path]]:
        """Move files into their category subdirectories.

        Args:
            categories: Mapping of category folder names to lists of FileInfo.
            progress_callback: Optional callable(current, total, filename).

        Returns:
            List of (source, destination) tuples for successful moves.
        """
        self._create_directories(categories)

        total = sum(len(files) for files in categories.values())
        current = 0

        for category, files in categories.items():
            dest_dir = self.source_dir / category

            for file_info in files:
                current += 1
                src = file_info.path

                try:
                    dest = dest_dir / file_info.name
                    dest = self._resolve_conflict(dest)

                    shutil.move(str(src), str(dest))
                    self.completed_moves.append((src, dest))

                    if progress_callback is not None:
                        progress_callback(current, total, file_info.name)

                except (PermissionError, OSError) as exc:
                    error_msg = f"{type(exc).__name__}: {exc}"
                    self.errors.append((file_info.name, error_msg))
                    logger.warning("Failed to move %s: %s", file_info.name, error_msg)

        return self.completed_moves

    def _resolve_conflict(self, dest: Path) -> Path:
        """Return an available destination path, appending _1, _2, etc. if needed."""
        if not dest.exists():
            return dest

        stem = dest.stem
        suffix = dest.suffix
        parent = dest.parent

        for i in range(1, 1000):
            candidate = parent / f"{stem}_{i}{suffix}"
            if not candidate.exists():
                return candidate

        raise OSError(f"Could not resolve naming conflict for {dest} after 999 attempts")

    def _create_directories(self, categories: dict[str, list[FileInfo]]) -> None:
        """Create subdirectories for each category."""
        for category in categories:
            dest_dir = self.source_dir / category
            dest_dir.mkdir(parents=True, exist_ok=True)
