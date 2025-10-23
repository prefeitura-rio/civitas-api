"""filesystem.py - File system operations.

Single responsibility: Handle file system operations and resolve working paths.
"""

import os
import tempfile
from pathlib import Path


class FileSystemService:
    """Handle file system operations following SRP."""

    _BASE_TEMP_DIR = Path(
        os.environ.get(
            "CLONING_REPORT_TMP_ROOT",
            Path(tempfile.gettempdir()) / "civitas" / "cloning_report",
        )
    )

    @classmethod
    def resolve_path(cls, path: str | Path) -> Path:
        """Resolve a path against the shared temp root when relative."""
        path_obj = Path(path)
        if not path_obj.is_absolute():
            path_obj = cls._BASE_TEMP_DIR / path_obj
        return path_obj

    @classmethod
    def ensure_directory(cls, path: str | Path) -> Path:
        """Create directory if it doesn't exist and return its path."""
        directory = cls.resolve_path(path)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @classmethod
    def get_base_temp_dir(cls) -> Path:
        """Expose the resolved base temp directory."""
        cls._BASE_TEMP_DIR.mkdir(parents=True, exist_ok=True)
        return cls._BASE_TEMP_DIR
