from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from app.modules.cloning_report.report import ReportPDF
    from app.modules.cloning_report.report.clonagem_report_generator.generator import (
        ClonagemReportGenerator,
    )


@dataclass(slots=True)
class BaseSectionRenderer:
    """Common base for PDF section renderers."""

    generator: ClonagemReportGenerator
    pdf: ReportPDF
