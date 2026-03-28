import re


INVALID_CHARS = r'[/\\:*?"<>|]'
MAX_NAME_LENGTH = 255
RESERVED_NAMES = {".", ".."}


def validate_folder_name(name: str) -> tuple[bool, str]:
    """Validate a folder name. Returns (is_valid, error_message)."""
    if not name or not name.strip():
        return False, "Folder name cannot be empty."
    if name != name.strip():
        return False, "Folder name should not start or end with spaces."
    if name in RESERVED_NAMES:
        return False, f'"{name}" is a reserved name.'
    if len(name) > MAX_NAME_LENGTH:
        return False, f"Folder name is too long (max {MAX_NAME_LENGTH} characters)."
    if re.search(INVALID_CHARS, name):
        return False, "Folder name contains invalid characters (/ \\ : * ? \" < > |)."
    return True, ""


def sanitize_folder_name(name: str) -> str:
    """Strip or replace invalid characters to produce a safe folder name."""
    name = name.strip()
    name = re.sub(INVALID_CHARS, "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    if not name or name in RESERVED_NAMES:
        name = "Folder"
    if len(name) > MAX_NAME_LENGTH:
        name = name[:MAX_NAME_LENGTH]
    return name
