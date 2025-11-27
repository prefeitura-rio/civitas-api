"""Table rendering functionality for PDF."""

import pandas as pd
from fpdf.enums import XPos, YPos
from app.modules.cloning_report.report.data_formatter import DataFormatter
from app.modules.cloning_report.report.style_manager import StyleManager
from app.modules.cloning_report.report.font_config import FontSize


class TableRenderer:
    """Handles table rendering in PDF."""

    def __init__(self, pdf_instance):
        self.pdf = pdf_instance
        self.style_manager = StyleManager(pdf_instance)

    def render_table(self, df: pd.DataFrame, title: str, text: str | None = None):
        """Render table with proper formatting"""
        df = DataFormatter.prepare_table_data(df)
        table_type = DataFormatter.identify_table_type(df)
        df = self._process_table_data(df, table_type)
        col_widths = self._calculate_column_widths(df, table_type)
        self._ensure_space_for_table(df, col_widths, text)
        self._add_table_header(title, text)
        self._draw_table_header(df, col_widths)
        self._draw_table_data(df, col_widths)
        self.pdf.ln(3)

    def _ensure_space_for_table(
        self, df: pd.DataFrame, col_widths: dict, text: str | None
    ) -> None:
        """Ensure header + first row fit on current page, otherwise start a new one."""
        header_h = 8
        line_h = 5.5
        bottom_limit = self.pdf.h - max(self.pdf.b_margin, 20)

        required_h = header_h + self._estimate_first_row_height(df, col_widths, line_h)
        required_h += self._estimate_title_block_height(text)

        if self.pdf.get_y() + required_h > bottom_limit:
            self.pdf.add_page()

    def _add_table_header(self, title: str, text: str | None):
        """Add table title and optional text"""
        self.pdf.set_font("Helvetica", "B", FontSize.TABLE_TITLE)
        self.pdf.cell(0, 10, title, new_x=XPos.CENTER, new_y=YPos.NEXT)
        self.pdf.ln(2)
        if text is not None:
            self.pdf.set_font("Helvetica", "", FontSize.BODY_TEXT)
            self.pdf.multi_cell(0, 5, text)
            self.pdf.ln(2)
        self.pdf.set_font("Helvetica", "", FontSize.BODY_TEXT)

    def _process_table_data(self, df: pd.DataFrame, table_type: str) -> pd.DataFrame:
        """Process table data based on table type"""
        if table_type == "clonagem":
            return DataFormatter.process_clonagem_data(df)
        elif table_type == "trilha":
            return DataFormatter.process_trilha_data(df)
        else:
            return df

    def _calculate_column_widths(self, df: pd.DataFrame, table_type: str) -> dict:
        """Calculate column widths based on table type"""
        if table_type == "clonagem":
            return self._get_clonagem_column_widths(df)
        elif table_type == "trilha":
            return self._get_trilha_column_widths()
        else:
            return self._get_generic_column_widths(df)

    def _get_clonagem_column_widths(self, df: pd.DataFrame) -> dict:
        """Get column widths for clonagem table"""
        cols_set = set(df.columns)
        if {"Latitude", "Longitude"}.issubset(cols_set):
            return {
                "Data": self.pdf.epw * 0.12,
                "Primeira Detecção": self.pdf.epw * 0.27,
                "Detecção Seguinte": self.pdf.epw * 0.27,
                "Latitude": self.pdf.epw * 0.17,
                "Longitude": self.pdf.epw * 0.17,
                "Km/h": self.pdf.epw * 0.10,
            }
        else:
            return {
                "Data": self.pdf.epw * 0.16,
                "Primeira Detecção": self.pdf.epw * 0.37,
                "Detecção Seguinte": self.pdf.epw * 0.37,
                "Km/h": self.pdf.epw * 0.10,
            }

    def _get_trilha_column_widths(self) -> dict:
        """Get column widths for trilha table"""
        return {
            "DataHora": self.pdf.epw * 0.20,
            "Local": self.pdf.epw * 0.42,
            "Bairro": self.pdf.epw * 0.16,
            "Latitude": self.pdf.epw * 0.11,
            "Longitude": self.pdf.epw * 0.11,
        }

    def _get_generic_column_widths(self, df: pd.DataFrame) -> dict:
        """Get column widths for generic table"""
        total_columns = len(df.columns)
        return {col: self.pdf.epw / max(1, total_columns) for col in df.columns}

    def _draw_table_header(self, df: pd.DataFrame, col_widths: dict):
        """Draw table header"""
        header_map = DataFormatter.get_header_mapping()
        headers = [header_map.get(col, col) for col in df.columns]

        header_h = 8
        self.style_manager.apply_table_header_style()

        for i, col in enumerate(df.columns):
            self.pdf.cell(
                col_widths[col],
                header_h,
                headers[i],
                border=1,
                align="C",
                fill=True,
                new_x=XPos.RIGHT,
                new_y=YPos.TOP,
            )
        self.pdf.ln(header_h)

    def _draw_table_data(self, df: pd.DataFrame, col_widths: dict):
        """Draw table data rows"""
        self.style_manager.apply_table_data_style()
        line_h = 5.5
        bottom_limit = self.pdf.h - max(self.pdf.b_margin, 20)

        for _, row in df.iterrows():
            self._draw_table_row(row, df.columns, col_widths, line_h, bottom_limit)

        self.pdf.ln(5)

    def _draw_table_row(self, row, columns, col_widths, line_h, bottom_limit):
        """Draw a single table row"""
        vals, nlines = self._prepare_row_data(row, columns, col_widths, line_h)
        row_h = max(nlines) * line_h

        if self.pdf.get_y() + row_h > bottom_limit:
            self._handle_page_break(columns, col_widths)

        self._render_row_cells(columns, vals, nlines, col_widths, row_h, line_h)

    def _prepare_row_data(self, row, columns, col_widths, line_h):
        """Prepare row data for rendering"""
        vals, nlines = [], []
        for col in columns:
            val = "" if pd.isna(row[col]) else str(row[col])
            vals.append(val)
            parts = self.pdf.multi_cell(
                col_widths[col],
                line_h,
                val,
                border=0,
                align="C",
                dry_run=True,
                output="LINES",
            )
            nlines.append(max(1, len(parts) if isinstance(parts, (list, tuple)) else 1))
        return vals, nlines

    def _render_row_cells(self, columns, vals, nlines, col_widths, row_h, line_h):
        """Render individual row cells"""
        y0 = self.pdf.get_y()
        ap = getattr(self.pdf, "auto_page_break", True)
        self.pdf.set_auto_page_break(False)

        for col, val, n in zip(columns, vals, nlines):
            self._draw_table_cell(col, val, n, col_widths, y0, row_h, line_h)

        self.pdf.set_auto_page_break(ap, margin=self.pdf.b_margin)
        self.pdf.set_y(y0 + row_h)

    def _draw_table_cell(self, col, val, n, col_widths, y0, row_h, line_h):
        """Draw a single table cell"""
        w = col_widths[col]
        x0 = self.pdf.get_x()

        try:
            self.pdf.rect(x0, y0, w, row_h, style="")
        except TypeError:
            self.pdf.rect(x0, y0, w, row_h)

        content_h = n * line_h
        y_txt = y0 + max(0, (row_h - content_h) / 2.0)
        self.pdf.set_xy(x0, y_txt)
        self.pdf.multi_cell(w, line_h, val, border=0, align="C")
        self.pdf.set_xy(x0 + w, y0)

    def _handle_page_break(self, columns, col_widths):
        """Handle page break by reprinting header"""
        self.pdf.add_page()
        self.style_manager.apply_table_header_style()
        header_map = DataFormatter.get_header_mapping()
        headers = [header_map.get(col, col) for col in columns]

        for i, col in enumerate(columns):
            self.pdf.cell(
                col_widths[col],
                8,
                headers[i],
                border=1,
                align="C",
                fill=True,
                new_x=XPos.RIGHT,
                new_y=YPos.TOP,
            )
        self.pdf.ln(8)
        self.style_manager.apply_table_data_style()

    def _estimate_first_row_height(
        self, df: pd.DataFrame, col_widths: dict, line_h: float
    ) -> float:
        """Measure the height of the first data row for pagination checks."""
        if df.empty:
            return 0.0

        # Use the same styling used when rendering rows for accurate measurement.
        self.style_manager.apply_table_data_style()
        _, nlines = self._prepare_row_data(df.iloc[0], df.columns, col_widths, line_h)
        return max(nlines) * line_h

    def _estimate_title_block_height(self, text: str | None) -> float:
        """Estimate the vertical space used by the table title and optional text."""
        title_h = 12.0  # cell height 10 + ln(2)
        if text is None:
            return title_h

        self.pdf.set_font("Helvetica", "", FontSize.BODY_TEXT)
        parts = self.pdf.multi_cell(
            0, 5, text, dry_run=True, output="LINES", align="L", border=0
        )
        line_count = len(parts) if isinstance(parts, (list, tuple)) else 1
        return title_h + max(1, line_count) * 5 + 2

    def render_params_table(self, rows: list[tuple[str, str]], *, label_w_ratio=0.38):
        """Render 2-column parameters table"""
        layout = self._calculate_params_table_layout(label_w_ratio)
        row_height = self._calculate_row_height(rows, layout)
        self._draw_params_table(rows, layout, row_height)

    def _calculate_params_table_layout(self, label_w_ratio: float) -> dict:
        """Calculate parameters table layout"""
        return {
            "line_h": 4.0,
            "pad_x": 2,
            "pad_y": 2,
            "x0": self.pdf.l_margin,
            "w": self.pdf.epw,
            "wL": self.pdf.epw * float(label_w_ratio),
            "wR": self.pdf.epw - (self.pdf.epw * float(label_w_ratio)),
        }

    def _calculate_row_height(self, rows: list, layout: dict) -> float:
        """Calculate uniform row height for all rows"""
        max_content_h = 0.0
        for lbl, val in rows:
            lbl_h = self._measure_content_height(lbl, layout["wL"], layout)
            val_h = self._measure_content_height(val, layout["wR"], layout)
            max_content_h = max(max_content_h, lbl_h, val_h)

        row_h = max_content_h + 2 * layout["pad_y"]
        return max(row_h, 12.0)

    def _measure_content_height(
        self, text: str, cell_width: float, layout: dict
    ) -> float:
        """Measure content height for a cell"""
        parts = self.pdf.multi_cell(
            cell_width - 2 * layout["pad_x"],
            layout["line_h"],
            str(text),
            dry_run=True,
            output="LINES",
        )
        n = max(1, len(parts) if isinstance(parts, (list, tuple)) else 1)
        return n * layout["line_h"]

    def _draw_params_table(self, rows: list, layout: dict, row_height: float):
        """Draw the parameters table"""
        self.pdf.set_font("Helvetica", "", FontSize.PARAMETERS_TABLE)
        self.pdf.set_draw_color(0, 0, 0)
        bottom_limit = self.pdf.h - max(self.pdf.b_margin, 17)
        y = self.pdf.get_y()

        for lbl, val in rows:
            y = self._draw_params_row(lbl, val, layout, row_height, y, bottom_limit)

        self.pdf.set_y(y + 3)

    def _draw_params_row(
        self,
        label: str,
        value: str,
        layout: dict,
        row_height: float,
        y: float,
        bottom_limit: float,
    ) -> float:
        """Draw a single parameters table row"""
        if y + row_height > bottom_limit:
            self.pdf.add_page()
            y = self.pdf.get_y()

        self.pdf.rect(layout["x0"], y, layout["wL"], row_height)
        self.pdf.rect(layout["x0"] + layout["wL"], y, layout["wR"], row_height)

        lbl_h = self._measure_content_height(label, layout["wL"], layout)
        val_h = self._measure_content_height(value, layout["wR"], layout)

        y_lbl = y + (row_height - lbl_h) / 2.0
        y_val = y + (row_height - val_h) / 2.0

        self._draw_cell_content(label, layout["x0"], y_lbl, layout["wL"], layout)
        self._draw_cell_content(
            value, layout["x0"] + layout["wL"], y_val, layout["wR"], layout
        )

        return y + row_height

    def _draw_cell_content(
        self, text: str, x: float, y: float, width: float, layout: dict
    ):
        """Draw cell content"""
        self.pdf.set_xy(x + layout["pad_x"], y)
        self.pdf.multi_cell(
            width - 2 * layout["pad_x"],
            layout["line_h"],
            str(text),
            border=0,
            align="L",
        )
