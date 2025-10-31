from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.cloning_report.report.pdf_sections import (
    CloningAnalysisRenderer,
    HowToReadRenderer,
    InstructionsPageRenderer,
    SummaryPageRenderer,
)

if TYPE_CHECKING:  # pragma: no cover - typing aid only
    from app.modules.cloning_report.report import ReportPDF


class ClonagemReportPDFMixin:
    """Thin mixin that delegates PDF rendering to dedicated section renderers."""

    def _add_all_pages(self, pdf: ReportPDF) -> None:
        self._add_instructions_page(pdf)
        self._add_summary_page(pdf)
        self._add_how_to_read_page(pdf)
        self._add_cloning_section(pdf)

    # --- high-level sections -------------------------------------------------
    def _add_instructions_page(self, pdf: ReportPDF) -> None:
        InstructionsPageRenderer(self, pdf).render()

    def _add_summary_page(self, pdf: ReportPDF) -> None:
        SummaryPageRenderer(self, pdf).render()

    def _add_how_to_read_page(self, pdf: ReportPDF) -> None:
        HowToReadRenderer(self, pdf).render()

    def _add_cloning_section(self, pdf: ReportPDF) -> None:
        CloningAnalysisRenderer(self, pdf).render()
