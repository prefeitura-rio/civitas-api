"""
filesystem.py - File system operations
-------------------------------------
Single responsibility: Handle file system operations
"""

from __future__ import annotations

import contextvars
import re
from pathlib import Path

CLONING_REPORT_ASSETS_MARKER = "app/assets/cloning_report"
CLONING_REPORT_TEMP_BASE = Path("/tmp") / "cloning_report"
_report_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "cloning_report_id", default=None
)


class FileSystemService:
    """Handle file system operations following SRP"""

    @staticmethod
    def ensure_directory(path: str | Path) -> Path:
        """Create directory if it doesn't exist"""
        directory = FileSystemService.resolve_path(path)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @staticmethod
    def resolve_path(path: str | Path) -> Path:
        """
        Resolve a path, redirecting cloning report asset paths to /tmp/cloning_report.

        This ensures that any writer targeting app/assets/cloning_report/* uses
        the temporary filesystem instead of the repository tree.
        """
        directory = Path(path)
        return FileSystemService._redirect_if_cloning_asset(directory)

    @staticmethod
    def set_report_context(report_id: str):
        """Activate report context so assets are isolated per report."""
        return _report_context.set(report_id)

    @staticmethod
    def reset_report_context(token) -> None:
        """Reset report context token."""
        if token is not None:
            _report_context.reset(token)

    @staticmethod
    def get_report_context() -> str | None:
        """Current report identifier, if any."""
        return _report_context.get()

    @staticmethod
    def get_report_temp_dir(report_id: str | None = None) -> Path:
        """Base directory for a report run under /tmp/cloning_report/<id>."""
        normalized = FileSystemService.normalize_report_id(
            report_id or FileSystemService.get_report_context()
        )
        if normalized:
            return CLONING_REPORT_TEMP_BASE / normalized
        return CLONING_REPORT_TEMP_BASE

    @staticmethod
    def normalize_report_id(report_id: str | None) -> str | None:
        """Normalize report ids so they are safe for filesystem usage."""
        if not report_id:
            return None
        return re.sub(r"[^A-Za-z0-9._-]+", "-", report_id)

    @staticmethod
    def build_unique_filename(base_name: str, report_id: str | None = None) -> str:
        """Append the report id suffix to filenames to avoid collisions."""
        normalized = FileSystemService.normalize_report_id(
            report_id or FileSystemService.get_report_context()
        )
        if not normalized:
            return base_name

        path = Path(base_name)
        stem = path.stem or path.name
        suffix = path.suffix
        return f"{stem}_{normalized}{suffix}"

    @staticmethod
    def build_unique_path(
        directory: str | Path, filename: str, report_id: str | None = None
    ) -> Path:
        """Return a full path with a report-specific filename."""
        target_dir = FileSystemService.ensure_directory(directory)
        unique_name = FileSystemService.build_unique_filename(filename, report_id)
        return target_dir / unique_name

    @staticmethod
    def _redirect_if_cloning_asset(directory: Path) -> Path:
        normalized = directory.as_posix()
        marker = CLONING_REPORT_ASSETS_MARKER

        if marker not in normalized:
            return directory

        suffix = normalized.split(marker, 1)[1].lstrip("/")
        base_dir = FileSystemService.get_report_temp_dir()

        if suffix:
            return base_dir / suffix
        return base_dir
