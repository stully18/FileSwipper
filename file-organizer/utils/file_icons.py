EXTENSION_ICONS: dict[str, str] = {
    # Documents
    ".pdf": "\U0001f4c4",
    ".doc": "\U0001f4c4",
    ".docx": "\U0001f4c4",
    ".odt": "\U0001f4c4",
    ".rtf": "\U0001f4c4",
    ".txt": "\U0001f4dd",
    ".md": "\U0001f4dd",
    ".csv": "\U0001f4ca",
    ".xls": "\U0001f4ca",
    ".xlsx": "\U0001f4ca",
    ".ods": "\U0001f4ca",
    ".ppt": "\U0001f4ca",
    ".pptx": "\U0001f4ca",
    ".odp": "\U0001f4ca",
    # Images
    ".jpg": "\U0001f5bc\ufe0f",
    ".jpeg": "\U0001f5bc\ufe0f",
    ".png": "\U0001f5bc\ufe0f",
    ".gif": "\U0001f5bc\ufe0f",
    ".bmp": "\U0001f5bc\ufe0f",
    ".svg": "\U0001f5bc\ufe0f",
    ".webp": "\U0001f5bc\ufe0f",
    ".ico": "\U0001f5bc\ufe0f",
    ".tiff": "\U0001f5bc\ufe0f",
    # Audio
    ".mp3": "\U0001f3b5",
    ".wav": "\U0001f3b5",
    ".flac": "\U0001f3b5",
    ".aac": "\U0001f3b5",
    ".ogg": "\U0001f3b5",
    ".wma": "\U0001f3b5",
    ".m4a": "\U0001f3b5",
    # Video
    ".mp4": "\U0001f3ac",
    ".avi": "\U0001f3ac",
    ".mkv": "\U0001f3ac",
    ".mov": "\U0001f3ac",
    ".wmv": "\U0001f3ac",
    ".flv": "\U0001f3ac",
    ".webm": "\U0001f3ac",
    # Archives
    ".zip": "\U0001f4e6",
    ".rar": "\U0001f4e6",
    ".7z": "\U0001f4e6",
    ".tar": "\U0001f4e6",
    ".gz": "\U0001f4e6",
    ".bz2": "\U0001f4e6",
    ".xz": "\U0001f4e6",
    ".deb": "\U0001f4e6",
    ".rpm": "\U0001f4e6",
    # Code
    ".py": "\U0001f40d",
    ".js": "\U0001f4bb",
    ".ts": "\U0001f4bb",
    ".html": "\U0001f310",
    ".css": "\U0001f3a8",
    ".java": "\U0001f4bb",
    ".c": "\U0001f4bb",
    ".cpp": "\U0001f4bb",
    ".h": "\U0001f4bb",
    ".rs": "\U0001f4bb",
    ".go": "\U0001f4bb",
    ".sh": "\U0001f4bb",
    ".json": "\U0001f4bb",
    ".xml": "\U0001f4bb",
    ".yaml": "\U0001f4bb",
    ".yml": "\U0001f4bb",
    ".sql": "\U0001f4bb",
    # Executables / installers
    ".exe": "\u2699\ufe0f",
    ".msi": "\u2699\ufe0f",
    ".AppImage": "\u2699\ufe0f",
    ".dmg": "\u2699\ufe0f",
    # Fonts
    ".ttf": "\U0001f524",
    ".otf": "\U0001f524",
    ".woff": "\U0001f524",
    ".woff2": "\U0001f524",
}

CATEGORY_ICONS: dict[str, str] = {
    "documents": "\U0001f4c4",
    "images": "\U0001f5bc\ufe0f",
    "photos": "\U0001f5bc\ufe0f",
    "audio": "\U0001f3b5",
    "music": "\U0001f3b5",
    "video": "\U0001f3ac",
    "videos": "\U0001f3ac",
    "archives": "\U0001f4e6",
    "code": "\U0001f4bb",
    "other": "\U0001f4c1",
}

DEFAULT_ICON = "\U0001f4c1"


def get_icon(extension: str) -> str:
    """Return an emoji icon for the given file extension."""
    return EXTENSION_ICONS.get(extension.lower(), DEFAULT_ICON)


def get_category_icon(category_name: str) -> str:
    """Return an emoji icon for a category name."""
    key = category_name.lower().replace("_", " ").replace("-", " ")
    for keyword, icon in CATEGORY_ICONS.items():
        if keyword in key:
            return icon
    return DEFAULT_ICON
