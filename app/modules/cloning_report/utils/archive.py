"""Helpers for bundling cloning report artifacts."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from collections.abc import Iterator

from fastapi import HTTPException

from app import config
from app.modules.cloning_report.utils.filesystem import FileSystemService
from app.modules.cloning_report.utils.logging import get_logger

logger = get_logger()

ZIP_STREAM_CHUNK_SIZE = 8192  # bytes per chunk when streaming the archive


def create_report_temp_dir(report_id: str) -> Path:
    """
    Create a dedicated temporary directory for a cloning report run.

    Artifacts generated during the request are stored under
    /tmp/cloning_report/<report_id>.
    """
    base_dir = FileSystemService.get_report_temp_dir(report_id)
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def resolve_pdf_path(report_path: str | Path | None) -> Path:
    """Validate and resolve the generated PDF path."""
    pdf_path = Path(report_path) if report_path else None
    if not pdf_path or not pdf_path.exists():
        logger.error(f"PDF file missing at {pdf_path}")
        raise HTTPException(status_code=500, detail="Generated PDF file not found")
    return pdf_path


def prepare_map_html(report_id: str, destination_dir: Path) -> Path | None:
    """
    Copy the generated cloning map HTML from /tmp/cloning_report to the destination
    directory used for bundling. Falls back to the repository asset when the
    runtime artifact is missing.
    """
    runtime_dir = FileSystemService.get_report_temp_dir(report_id) / "htmls"
    generated_name = FileSystemService.build_unique_filename(
        "mapa_clonagem.html", report_id
    )
    source = runtime_dir / generated_name

    if not source.exists():
        base_source = (
            config.ASSETS_DIR / "cloning_report" / "htmls" / "mapa_clonagem.html"
        )
        if base_source.exists():
            source = base_source
        else:
            logger.warning(f"HTML source file not found: {source}")
            return None

    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"mapa_clonagem_{report_id}.html"

    try:
        shutil.copy(source, destination)
        if destination.exists():
            return destination
    except Exception:  # pragma: no cover - defensive logging
        logger.error(f"Failed to copy cloning map HTML from {source} to {destination}")
    return None


def generate_report_bundle_stream(
    pdf_path: Path, html_path: Path | None
) -> Iterator[bytes]:
    """
    Stream a ZIP containing the cloning report PDF and optional HTML map.

    The ZIP archive is written to disk and kept for auditability; the
    individual PDF/HTML artifacts are removed once the bundle is ready.
    """
    zip_path = pdf_path.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(pdf_path, arcname=pdf_path.name)
        if html_path:
            zf.write(html_path, arcname="mapa_clonagem.html")

    try:
        pdf_path.unlink(missing_ok=False)  # Python 3.8 lacks missing_ok
    except FileNotFoundError:
        logger.warning(f"PDF already removed before cleanup: {pdf_path}")
    except Exception:  # pragma: no cover - defensive logging
        logger.error(f"Failed to remove PDF artifact {pdf_path}")

    if html_path:
        try:
            html_path.unlink()
        except FileNotFoundError:
            logger.warning(f"HTML already removed before cleanup: {html_path}")
        except Exception:  # pragma: no cover - defensive logging
            logger.error(f"Failed to remove HTML artifact {html_path}")

    with zip_path.open("rb") as zip_file:
        while True:
            chunk = zip_file.read(ZIP_STREAM_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
