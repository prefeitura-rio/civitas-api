"""
filesystem.py - File system operations
-------------------------------------
Single responsibility: Handle file system operations
"""

import tempfile
from pathlib import Path


class FileSystemService:
    """Handle file system operations following SRP"""

    _TMP_ROOT_NAME = "cloning_report"

    @staticmethod
    def ensure_directory(path: str | Path) -> Path:
        """Create directory if it doesn't exist"""
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @classmethod
    def get_temp_root(cls) -> Path:
        """Return base temporary directory for cloning report assets"""
        root = Path(tempfile.gettempdir()) / cls._TMP_ROOT_NAME
        return cls.ensure_directory(root)

    @classmethod
    def get_temp_dir(cls, *parts: str) -> Path:
        """Return/create subdirectory inside the cloning_report temp root"""
        return cls.ensure_directory(cls.get_temp_root().joinpath(*parts))
