"""filesystem.py - File system operations.

Single responsibility: Handle file system operations and resolve working paths.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path


class FileSystemService:
    """Handle file system operations following SRP."""

    _BASE_TEMP_DIR = Path(
        os.environ.get(
            "CLONING_REPORT_TMP_ROOT",
            Path(tempfile.gettempdir()) / "civitas" / "cloning_report",
        )
    )
    _context_root: ContextVar[Path | None] = ContextVar(
        "cloning_report_temp_root", default=None
    )

    @classmethod
    def resolve_path(cls, path: str | Path) -> Path:
        """Resolve a path against the active report root when relative."""
        path_obj = Path(path)
        if path_obj.is_absolute():
            return path_obj

        context_root = cls._context_root.get()
        base = context_root if context_root is not None else cls.get_base_temp_dir()
        return base / path_obj

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

    @classmethod
    @contextmanager
    def use_temp_root(cls, root: Path):
        """Temporarily set the working root for generated artifacts."""
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        token = cls._context_root.set(root)
        try:
            yield root
        finally:
            cls._context_root.reset(token)
