"""PDF cleanup utilities for cloning reports"""

# import os
import time
from datetime import datetime
from pathlib import Path

from app.modules.cloning_report.utils import get_logger

logger = get_logger()


class PDFCleanupService:
    """Service for cleaning up generated PDF reports"""

    def __init__(self, reports_dir: str = "reports", max_age_hours: int = 24):
        """
        Initialize PDF cleanup service

        Args:
            reports_dir: Directory where reports are stored
            max_age_hours: Maximum age in hours before PDF is deleted
        """
        self.reports_dir = Path(reports_dir)
        self.max_age_hours = max_age_hours
        self.max_age_seconds = max_age_hours * 3600

    def cleanup_old_pdfs(self) -> int:
        """
        Remove PDFs older than max_age_hours

        Returns:
            Number of files deleted
        """
        if not self.reports_dir.exists():
            logger.info(f"Reports directory {self.reports_dir} does not exist")
            return 0

        deleted_count = 0
        current_time = time.time()

        for pdf_file in self.reports_dir.glob("*.pdf"):
            try:
                file_age = current_time - pdf_file.stat().st_mtime

                if file_age > self.max_age_seconds:
                    logger.info(
                        f"Deleting old PDF: {pdf_file.name} (age: {file_age / 3600:.1f}h)"
                    )
                    pdf_file.unlink()
                    deleted_count += 1
                else:
                    logger.debug(
                        f"Keeping PDF: {pdf_file.name} (age: {file_age / 3600:.1f}h)"
                    )

            except Exception:
                logger.exception(f"Error deleting {pdf_file.name}")

        logger.info(f"PDF cleanup completed: {deleted_count} files deleted")
        return deleted_count

    def cleanup_by_pattern(self, pattern: str = "relatorio_clonagem_*") -> int:
        """
        Remove PDFs matching a specific pattern

        Args:
            pattern: Glob pattern to match files

        Returns:
            Number of files deleted
        """
        if not self.reports_dir.exists():
            return 0

        deleted_count = 0

        for pdf_file in self.reports_dir.glob(pattern):
            try:
                logger.info(f"Deleting PDF: {pdf_file.name}")
                pdf_file.unlink()
                deleted_count += 1
            except Exception:
                logger.exception(f"Error deleting {pdf_file.name}")

        logger.info(f"Pattern cleanup completed: {deleted_count} files deleted")
        return deleted_count

    def get_pdf_info(self) -> list[dict]:
        """
        Get information about all PDFs in the reports directory

        Returns:
            List of dictionaries with PDF information
        """
        if not self.reports_dir.exists():
            return []

        pdf_info = []
        current_time = time.time()

        for pdf_file in self.reports_dir.glob("*.pdf"):
            try:
                stat = pdf_file.stat()
                age_hours = (current_time - stat.st_mtime) / 3600

                pdf_info.append(
                    {
                        "name": pdf_file.name,
                        "size_bytes": stat.st_size,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "age_hours": round(age_hours, 2),
                        "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "path": str(pdf_file),
                    }
                )
            except Exception:
                logger.exception(f"Error getting info for {pdf_file.name}")

        return sorted(pdf_info, key=lambda x: x["age_hours"], reverse=True)

    def cleanup_specific_plate(self, plate: str) -> int:
        """
        Remove all PDFs for a specific plate

        Args:
            plate: Plate number to clean up

        Returns:
            Number of files deleted
        """
        pattern = f"relatorio_clonagem_{plate}_*"
        return self.cleanup_by_pattern(pattern)


# Global cleanup service instance
_cleanup_service: PDFCleanupService | None = None


def get_cleanup_service() -> PDFCleanupService:
    """Get global PDF cleanup service instance"""
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = PDFCleanupService()
    return _cleanup_service


def cleanup_old_pdfs(max_age_hours: int = 24) -> int:
    """Convenience function to cleanup old PDFs"""
    service = get_cleanup_service()
    service.max_age_hours = max_age_hours
    return service.cleanup_old_pdfs()


def cleanup_plate_pdfs(plate: str) -> int:
    """Convenience function to cleanup PDFs for a specific plate"""
    service = get_cleanup_service()
    return service.cleanup_specific_plate(plate)
