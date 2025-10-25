"""Convenience helpers for cloning report filesystem layout."""

from __future__ import annotations

import re
from contextlib import contextmanager, nullcontext
from datetime import datetime
from pathlib import Path

from app.modules.cloning_report.utils.filesystem import FileSystemService


class ReportPaths:
    """Centralized access to filesystem locations used by the cloning report."""

    _DEFAULT_ROOT_PREFIX = "report"

    @staticmethod
    def base_dir() -> Path:
        """Return the root directory for all generated artifacts."""
        return FileSystemService.get_base_temp_dir()

    @classmethod
    def ensure(cls, *segments: str) -> Path:
        """Ensure a directory relative to the base exists and return its Path."""
        relative = Path(*segments)
        return FileSystemService.ensure_directory(relative)

    @classmethod
    def temp_html_dir(cls) -> Path:
        """Directory that stores intermediate HTML files."""
        return cls.ensure("temp", "html")

    @classmethod
    def figures_dir(cls) -> Path:
        """Directory that stores generated PNG artifacts."""
        return cls.ensure("figures")

    @classmethod
    def analytics_dir(cls) -> Path:
        """Directory for analytics assets."""
        return cls.ensure("analytics")

    @classmethod
    def detection_dir(cls) -> Path:
        """Directory for detection pipeline exports."""
        return cls.ensure("detection")

    # ------------------------------------------------------------------
    # Convenience helpers that return full file paths
    # ------------------------------------------------------------------
    @classmethod
    def temp_html_path(cls, filename: str) -> Path:
        return cls.temp_html_dir() / filename

    @classmethod
    def figure_path(cls, filename: str) -> Path:
        return cls.figures_dir() / filename

    @classmethod
    def analytics_path(cls, filename: str) -> Path:
        return cls.analytics_dir() / filename

    @classmethod
    def detection_path(cls, filename: str) -> Path:
        return cls.detection_dir() / filename

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------
    @classmethod
    @contextmanager
    def use_report_root(cls, identifier: str | None):
        """Temporarily scope paths to a specific report identifier."""
        name = cls.to_directory_name(identifier)
        root = cls.base_dir() / name
        with FileSystemService.use_temp_root(root):
            yield root

    @classmethod
    def to_directory_name(cls, identifier: str | None) -> str:
        """Sanitize any identifier into a filesystem-friendly directory name."""
        if not identifier:
            identifier = f"{cls._DEFAULT_ROOT_PREFIX}_{datetime.now():%Y%m%d_%H%M%S}"
        sanitized = re.sub(r"[^0-9A-Za-z._-]", "_", identifier).strip("._-")
        return sanitized or cls._DEFAULT_ROOT_PREFIX

    @classmethod
    def current_root(cls) -> Path:
        """Return the currently active root (for diagnostics)."""
        # Using ensure() with empty path would respect the context root without creating
        # additional directories; instead, inspect the resolved base directly.
        # The use_temp_root context ensures the directory exists.
        return FileSystemService.resolve_path(".").resolve()

    @classmethod
    def optional_report_context(cls, identifier: str | None):
        """Return a context manager that scopes paths when identifier is provided."""
        if identifier:
            return cls.use_report_root(identifier)
        return nullcontext()


__all__ = ["ReportPaths"]
