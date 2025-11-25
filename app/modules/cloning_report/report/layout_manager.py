"""PDF layout management for headers, footers, and positioning."""

import os
import random
from fpdf import FPDF
from datetime import datetime

from app.modules.cloning_report.report.font_config import FontSize


class PDFLayoutManager:
    """Manages PDF layout including headers, footers, and positioning."""

    def __init__(self, pdf_instance: FPDF):
        self.pdf = pdf_instance

    def setup_header(self, report_id: str | None = None):
        """Build PDF header - refactored with max 5 lines per method"""
        self.report_id = report_id
        layout = self._calculate_header_layout()
        self._draw_header_border(layout)
        self._add_logos(layout)
        self._add_title(layout)
        self._add_id_line(layout)
        self._advance_cursor(layout)

    def _generate_report_id(self):
        """Generate unique report ID"""
        now = datetime.now()
        return f"{now.strftime('%Y%m%d.%H%M%S')}{random.randint(0, 999):03d}"

    def _calculate_header_layout(self):
        """Calculate header layout dimensions"""
        margin = 10
        page_width = self.pdf.w
        usable_width = page_width - 2 * margin
        return {
            "margin": margin,
            "page_width": page_width,
            "usable_width": usable_width,
            "col1_width": usable_width * 0.30,
            "col2_width": usable_width * 0.70,
            "row1_height": 20,
            "row2_height": 10,
            "y_start": self.pdf.get_y(),
        }

    def _draw_header_border(self, layout):
        """Draw header border"""
        self.pdf.set_xy(layout["margin"], layout["y_start"])
        self.pdf.set_font("Helvetica", "B", FontSize.HEADER_TITLE)
        self.pdf.set_draw_color(0, 0, 0)
        self.pdf.cell(layout["col1_width"], layout["row1_height"], "", border=1)

    def _add_logos(self, layout):
        """Add logos to header"""
        prefeitura_path = "app/assets/logo_prefeitura.png"
        civitas_path = "app/assets/logo_civitas.png"

        if not (os.path.exists(prefeitura_path) and os.path.exists(civitas_path)):
            return

        logo_pos = self._calculate_logo_positions(layout)
        self._place_logos(prefeitura_path, civitas_path, logo_pos)

    def _calculate_logo_positions(self, layout):
        """Calculate logo positions"""
        logo_spacing = 5
        prefeitura_w = 16
        civitas_w = 31
        max_h = 12

        x_logo_start = (
            layout["margin"]
            + (layout["col1_width"] - (prefeitura_w + civitas_w + logo_spacing)) / 2
        )
        y_logo_start = layout["y_start"] + (layout["row1_height"] - max_h) / 2

        return {
            "x_start": x_logo_start,
            "y_start": y_logo_start,
            "prefeitura_w": prefeitura_w,
            "civitas_w": civitas_w,
            "spacing": logo_spacing,
        }

    def _place_logos(self, prefeitura_path, civitas_path, pos):
        """Place logos on PDF"""
        self.pdf.image(
            prefeitura_path, x=pos["x_start"], y=pos["y_start"], w=pos["prefeitura_w"]
        )
        self.pdf.image(
            civitas_path,
            x=pos["x_start"] + pos["prefeitura_w"] + pos["spacing"],
            y=pos["y_start"],
            w=pos["civitas_w"],
        )

    def _add_title(self, layout):
        """Add title to header"""
        self.pdf.set_xy(layout["margin"] + layout["col1_width"], layout["y_start"])
        self.pdf.set_font("Helvetica", "B", FontSize.HEADER_TITLE)
        self.pdf.cell(
            layout["col2_width"],
            layout["row1_height"],
            "RELATÓRIO DE SUSPEITA DE CLONAGEM",
            border=1,
            align="C",
        )

    def _add_id_line(self, layout):
        """Add ID line to header"""
        self.pdf.set_xy(layout["margin"], layout["y_start"] + layout["row1_height"])
        self.pdf.set_font("Helvetica", "", FontSize.HEADER_ID)
        self.pdf.cell(
            layout["usable_width"],
            layout["row2_height"],
            f"ID: {self.report_id}",
            border=1,
            align="C",
        )

    def _advance_cursor(self, layout):
        """Advance cursor after header"""
        self.pdf.set_y(
            layout["y_start"] + layout["row1_height"] + layout["row2_height"] + 5
        )

    def setup_footer(self):
        """Setup PDF footer"""
        self.pdf.set_y(-15)
        self.pdf.set_font("Helvetica", "I", 8)
        disclaimer = (
            "Este relatório foi gerado automaticamente a partir dos dados do sistema Cerco Digital. "
            "Como material de apoio, é também disponibilizado automaticamente um arquivo HTML "
            "com mapas interativos."
        )
        self.pdf.multi_cell(0, 5, disclaimer, align="C")
        self.pdf.set_font("Helvetica", "", 8)
        self.pdf.cell(0, 5, f"Página {self.pdf.page_no()} / {{nb}}", align="C")
