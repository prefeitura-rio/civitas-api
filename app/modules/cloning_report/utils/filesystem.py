"""
filesystem.py - File system operations
-------------------------------------
Single responsibility: Handle file system operations
"""

from pathlib import Path


class FileSystemService:
    """Handle file system operations following SRP"""

    @staticmethod
    def ensure_directory(path: str | Path) -> Path:
        """Create directory if it doesn't exist"""
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        return directory
