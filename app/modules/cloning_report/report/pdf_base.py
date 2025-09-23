"""Refactored PDF base class that orchestrates specialized components."""

from fpdf import FPDF
import pandas as pd
from .layout_manager import PDFLayoutManager
from .content_renderer import ContentRenderer
from .table_renderer import TableRenderer


class ReportPDF(FPDF):
    """Main PDF class that orchestrates layout, content, and styling components."""
    
    def __init__(self):
        super().__init__()
        self.layout_manager = PDFLayoutManager(self)
        self.content_renderer = ContentRenderer(self)
        self.table_renderer = TableRenderer(self)
    
    def header(self):
        """Build PDF header using layout manager"""
        self.layout_manager.setup_header()

    def footer(self):
        """Build PDF footer using layout manager"""
        self.layout_manager.setup_footer()

    # ---------- Content rendering methods (delegate to content_renderer) ----------
    def chapter_title(self, title):
        """Render chapter title"""
        self.content_renderer.render_chapter_title(title)

    def sub_title(self, title):
        """Render sub title"""
        self.content_renderer.render_sub_title(title)

    def chapter_body(self, body: str):
        """Render chapter body"""
        self.content_renderer.render_chapter_body(body)

    def chapter_html(self, html_body: str, *, font_family: str = "LiberationSans", 
                    font_size_pt: int = 10, line_step_mm: float = 5.0) -> None:
        """Render HTML content"""
        self.content_renderer.render_chapter_html(html_body, font_family=font_family,
                                                  font_size_pt=font_size_pt, line_step_mm=line_step_mm)

    def add_kpi_box(self, title, value, x, y, w=40, h=47, num_suspeitos=0, 
                   pad_x=5, pad_top=6, pad_bottom=6):
        """Add KPI box"""
        self.content_renderer.render_kpi_box(title, value, x, y, w, h, num_suspeitos, 
                                           pad_x, pad_top, pad_bottom)

    def add_figure(self, fig_or_path, title, text: str | None = None, width_factor: float = 0.90):
        """Add figure"""
        self.content_renderer.render_figure(fig_or_path, title, text, width_factor)

    def add_params_table(self, rows: list[tuple[str, str]], *, label_w_ratio=0.38):
        """Add parameters table"""
        self.content_renderer.render_params_table(rows, label_w_ratio=label_w_ratio)

    # ---------- Table rendering methods (delegate to table_renderer) ----------
    def add_table(self, df: pd.DataFrame, title: str, text: str | None = None):
        """Add table to PDF"""
        self.table_renderer.render_table(df, title, text)