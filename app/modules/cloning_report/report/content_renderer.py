"""Content rendering for text, tables, figures, and KPI boxes."""

import os
from io import BytesIO
from fpdf.enums import XPos, YPos
from fpdf import TextStyle
from app.modules.cloning_report.report.font_config import FontSize


class ContentRenderer:
    """Handles rendering of various content types in PDF."""

    def __init__(self, pdf_instance):
        self.pdf = pdf_instance

    def render_chapter_title(self, title):
        """Render chapter title"""
        self.pdf.set_font("Helvetica", "B", FontSize.CHAPTER_TITLE)
        self.pdf.cell(0, 10, title, new_x=XPos.CENTER, new_y=YPos.NEXT)
        self.pdf.ln(2)

    def render_sub_title(self, title):
        """Render sub title"""
        self.pdf.set_font("Helvetica", "B", FontSize.SECTION_TITLE)
        self.pdf.cell(0, 10, title, new_x=XPos.CENTER, new_y=YPos.NEXT)
        self.pdf.ln(2)

    def render_chapter_body(self, body: str):
        """Render chapter body text"""
        self.pdf.set_font("Helvetica", "", FontSize.BODY_TEXT)
        self.pdf.multi_cell(0, 5, body)
        self.pdf.ln(2)

    def render_chapter_html(
        self,
        html_body: str,
        *,
        font_family: str = "Helvetica",
        font_size_pt: int = 10,
        line_step_mm: float = 5.0,
    ) -> None:
        """Render HTML content with consistent formatting"""
        lh_factor = line_step_mm / (font_size_pt * 0.3527777778)
        html = self._build_html_content(html_body, font_family, font_size_pt, lh_factor)
        tag_styles = {"p": TextStyle(t_margin=0, b_margin=0)}
        self.pdf.write_html(html, font_family=font_family, tag_styles=tag_styles)
        self.pdf.ln(2)

    def _build_html_content(self, html_body, font_family, font_size_pt, lh_factor):
        """Build HTML content string"""
        return (
            f'<font face="{font_family}" size="{font_size_pt}">'
            f'<p line-height="{lh_factor:.3f}">{html_body}</p>'
            f"</font>"
        )

    def render_kpi_box(
        self,
        title,
        value,
        x,
        y,
        w=40,
        h=47,
        num_suspeitos=0,
        pad_x=5,
        pad_top=6,
        pad_bottom=6,
    ):
        """Render KPI box with title, value and icon"""
        from .kpi_renderer import KPIRenderer

        kpi_renderer = KPIRenderer(self.pdf)
        kpi_renderer.render_kpi_box(
            title, value, x, y, w, h, num_suspeitos, pad_x, pad_top, pad_bottom
        )

    def render_figure(
        self, fig_or_path, title, text: str | None = None, width_factor: float = 0.90
    ):
        """Render figure with title and optional text"""
        self.render_sub_title(title)
        if text is not None:
            self.render_chapter_body(text)

        img_width = self.pdf.epw * float(width_factor)
        x_pos = (self.pdf.w - img_width) / 2

        if isinstance(fig_or_path, str):
            self._render_file_figure(fig_or_path, x_pos, img_width)
        else:
            self._render_object_figure(fig_or_path, x_pos, img_width)
        self.pdf.ln(5)

    def _render_file_figure(self, fig_path, x_pos, img_width):
        """Render figure from file path"""
        if not os.path.exists(fig_path):
            self.pdf.set_font("Helvetica", "I", 10)
            self.pdf.multi_cell(0, 5, f"Figura não encontrada: {fig_path}")
            self.pdf.ln(4)
            return
        self.pdf.image(fig_path, x=x_pos, w=img_width)

    def _render_object_figure(self, fig_object, x_pos, img_width):
        """Render figure from object"""
        buf = BytesIO()
        fig_object.savefig(buf, format="png", bbox_inches="tight", dpi=350)
        buf.seek(0)
        self.pdf.image(buf, x=x_pos, w=img_width)
        buf.close()

    def render_params_table(self, rows: list[tuple[str, str]], *, label_w_ratio=0.38):
        """Render 2-column parameters table"""
        from .table_renderer import TableRenderer

        table_renderer = TableRenderer(self.pdf)
        table_renderer.render_params_table(rows, label_w_ratio=label_w_ratio)
