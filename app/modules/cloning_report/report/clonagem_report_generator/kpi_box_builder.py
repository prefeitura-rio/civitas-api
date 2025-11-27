from app.modules.cloning_report.report import ReportPDF


class KpiBoxBuilder:
    def _store_kpi_layout(self):
        self._kpi_layout = {**self._kpi_dims, **self._kpi_pos}

    def _add_total_records_box(self, pdf: ReportPDF, layout):
        pdf.add_kpi_box(
            "Número total de registros",
            str(self.total_deteccoes),
            layout["col_x"][0],
            layout["y0"],
            layout["box_w"],
            layout["row_h1"],
        )

    def _add_suspicious_records_box(self, pdf: ReportPDF, layout):
        num_txt = str(self.num_suspeitos) if self.num_suspeitos > 0 else "0"
        pdf.add_kpi_box(
            "Número de registros suspeitos",
            num_txt,
            layout["col_x"][1],
            layout["y0"],
            layout["box_w"],
            layout["row_h1"],
        )

    def _add_most_suspicious_day_box(self, pdf: ReportPDF, layout):
        dia_txt = self.dia_mais_sus if self.dia_mais_sus != "N/A" else "N/A"
        if self.dia_mais_sus != "N/A":
            dia_txt = f"{self.dia_mais_sus} ({self.sus_dia_mais_sus})"
        pdf.add_kpi_box(
            "Dia com mais registros suspeitos",
            dia_txt,
            layout["col_x"][2],
            layout["y0"],
            layout["box_w"],
            layout["row_h1"],
        )

    def _calculate_kpi_dimensions(self, pdf: ReportPDF):
        col_gap = 8
        cols = 3
        box_w = (pdf.epw - (cols - 1) * col_gap) / cols
        row_h1 = 50
        self._kpi_dims = {
            "col_gap": col_gap,
            "cols": cols,
            "box_w": box_w,
            "row_h1": row_h1,
        }

    def _calculate_kpi_positions(self, pdf: ReportPDF):
        y0 = pdf.get_y()
        col_x = [
            pdf.l_margin + i * (self._kpi_dims["box_w"] + self._kpi_dims["col_gap"])
            for i in range(self._kpi_dims["cols"])
        ]
        self._kpi_pos = {"y0": y0, "col_x": col_x}

    def setup_kpi_layout(self, pdf: ReportPDF):
        self._calculate_kpi_dimensions(pdf)
        self._calculate_kpi_positions(pdf)
        self._store_kpi_layout()

    def add_kpi_boxes_content(self, pdf: ReportPDF):
        layout = self._kpi_layout
        self._add_total_records_box(pdf, layout)
        self._add_suspicious_records_box(pdf, layout)
        self._add_most_suspicious_day_box(pdf, layout)
