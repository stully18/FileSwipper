from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileInfo:
    path: Path
    name: str
    extension: str
    size: int
    modified: float


@dataclass
class CategorySuggestion:
    folder_name: str
    description: str
    files: list[FileInfo] = field(default_factory=list)


@dataclass
class OrganizePlan:
    source_dir: Path
    files: list[FileInfo] = field(default_factory=list)
    categories: dict[str, list[FileInfo]] = field(default_factory=dict)
    moves: list[tuple[Path, Path]] = field(default_factory=list)
