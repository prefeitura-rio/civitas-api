"""Helpers for bundling cloning report artifacts."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from collections.abc import Iterator

from fastapi import HTTPException

from app import config
from app.modules.cloning_report.utils.logging import get_logger

logger = get_logger()


def create_report_temp_dir(report_id: str) -> Path:
    """Create a dedicated temporary directory for a cloning report run."""
    base_dir = Path(tempfile.gettempdir()) / "cloning_report" / report_id
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def resolve_pdf_path(report_path: str | Path | None) -> Path:
    """Validate and resolve the generated PDF path."""
    pdf_path = Path(report_path) if report_path else None
    if not pdf_path or not pdf_path.exists():
        logger.error(f"PDF file missing at {pdf_path}")
        raise HTTPException(status_code=500, detail="Generated PDF file not found")
    return pdf_path


def prepare_map_html(report_id: str) -> Path | None:
    """Copy the static cloning map HTML to a temporary location for bundling."""
    source = config.ASSETS_DIR / "cloning_report" / "htmls" / "mapa_clonagem.html"
    if not source.exists():
        logger.warning(f"HTML source file not found: {source}")
        return None

    destination_dir = Path(tempfile.gettempdir()) / "cloning_report_html"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"mapa_clonagem_{report_id}.html"

    try:
        shutil.copy(source, destination)
        if destination.exists():
            return destination
    except Exception as error:  # pragma: no cover - defensive logging
        logger.error(
            f"Failed to copy cloning map HTML from {source} to {destination}: {error}"
        )
    return None


def generate_report_bundle_stream(
    pdf_path: Path, html_path: Path | None, *, cleanup_pdf: bool = True
) -> Iterator[bytes]:
    """
    Stream a ZIP containing the cloning report PDF and optional HTML map.

    Temporary artifacts are removed after the stream is exhausted to keep /tmp tidy.
    """
    zip_buffer = BytesIO()
    try:
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(pdf_path, arcname=pdf_path.name)
            if html_path:
                zf.write(html_path, arcname="mapa_clonagem.html")

        zip_buffer.seek(0)
        while True:
            chunk = zip_buffer.read(8192)
            if not chunk:
                break
            yield chunk
    finally:
        zip_buffer.close()
        if cleanup_pdf:
            try:
                pdf_path.unlink(missing_ok=True)
                _cleanup_directory_if_empty(pdf_path.parent)
            except Exception as cleanup_error:  # pragma: no cover
                logger.warning(
                    f"Failed to remove temporary PDF {pdf_path}: {cleanup_error}"
                )
        if html_path:
            try:
                html_path.unlink(missing_ok=True)
                _cleanup_directory_if_empty(html_path.parent)
            except Exception as cleanup_error:  # pragma: no cover
                logger.warning(
                    f"Failed to remove temporary HTML map {html_path}: {cleanup_error}"
                )


def _cleanup_directory_if_empty(path: Path) -> None:
    """Remove the directory if it is empty."""
    try:
        path.rmdir()
    except FileNotFoundError:
        return
    except OSError:
        # Directory not empty - perfectly fine to leave it in /tmp
        return
    except Exception as error:  # pragma: no cover
        logger.warning(f"Failed to remove temporary directory {path}: {error}")
