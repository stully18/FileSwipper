from pathlib import Path
from collections import Counter, defaultdict
from typing import Callable

from . import FileInfo

# Mapping of file extensions to human-readable type categories.
_EXTENSION_CATEGORIES: dict[str, str] = {}
_CATEGORY_EXTENSIONS: dict[str, list[str]] = {
    "Documents": [
        ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx",
        ".ppt", ".pptx", ".csv", ".pages", ".numbers", ".keynote", ".epub",
        ".md", ".tex", ".log",
    ],
    "Images": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff",
        ".tif", ".ico", ".heic", ".heif", ".raw", ".psd", ".ai", ".eps",
    ],
    "Audio": [
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".aiff",
        ".alac", ".opus", ".mid", ".midi",
    ],
    "Video": [
        ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v",
        ".mpeg", ".mpg", ".3gp", ".ts",
    ],
    "Archives": [
        ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz", ".iso",
        ".dmg", ".pkg", ".deb", ".rpm", ".tgz",
    ],
    "Code": [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
        ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt",
        ".scala", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".sql",
        ".html", ".css", ".scss", ".sass", ".less", ".json", ".xml",
        ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".r", ".m",
        ".lua", ".pl", ".pm", ".ex", ".exs", ".erl", ".hs", ".dart",
        ".vue", ".svelte",
    ],
}
for _category, _extensions in _CATEGORY_EXTENSIONS.items():
    for _ext in _extensions:
        _EXTENSION_CATEGORIES[_ext] = _category


class DirectoryAnalyzer:
    """Analyzes a directory's files for the AI organizer."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def scan(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[FileInfo]:
        """List top-level files (non-recursive, no subdirectories).

        Calls *progress_callback(current, total)* every 50 files when provided.
        Skips files that raise PermissionError.
        """
        try:
            entries = [e for e in self.path.iterdir() if e.is_file()]
        except PermissionError:
            return []

        total = len(entries)
        files: list[FileInfo] = []

        for i, entry in enumerate(entries, start=1):
            try:
                stat = entry.stat()
                files.append(
                    FileInfo(
                        path=entry,
                        name=entry.name,
                        extension=entry.suffix.lower(),
                        size=stat.st_size,
                        modified=stat.st_mtime,
                    )
                )
            except PermissionError:
                continue

            if progress_callback is not None and (i % 50 == 0 or i == total):
                progress_callback(i, total)

        return files

    def group_by_extension(
        self, files: list[FileInfo]
    ) -> dict[str, list[FileInfo]]:
        """Group files by extension. Files without an extension go under 'No Extension'."""
        groups: dict[str, list[FileInfo]] = defaultdict(list)
        for f in files:
            key = f.extension if f.extension else "No Extension"
            groups[key].append(f)
        return dict(groups)

    def get_summary_for_ai(self, files: list[FileInfo]) -> str:
        """Build a compact text summary suitable for an AI prompt.

        Includes total file count, extension breakdown sorted by frequency,
        and up to 30 sample filenames.
        """
        total = len(files)
        ext_counts = Counter(
            f.extension if f.extension else "No Extension" for f in files
        )
        sorted_exts = ext_counts.most_common()

        lines: list[str] = []
        lines.append(f"Total files: {total}")
        lines.append("")
        lines.append("Extension breakdown:")
        for ext, count in sorted_exts:
            lines.append(f"  {ext}: {count}")

        sample_names = [f.name for f in files[:30]]
        lines.append("")
        lines.append(f"Sample filenames ({len(sample_names)} of {total}):")
        for name in sample_names:
            lines.append(f"  {name}")

        return "\n".join(lines)

    def get_type_summary(self, files: list[FileInfo]) -> dict[str, int]:
        """Return a dict mapping human-readable type categories to file counts.

        Categories: Documents, Images, Audio, Video, Archives, Code, Other.
        """
        counts: dict[str, int] = defaultdict(int)
        for f in files:
            category = _EXTENSION_CATEGORIES.get(f.extension, "Other")
            if not f.extension:
                category = "Other"
            counts[category] += 1
        return dict(counts)
