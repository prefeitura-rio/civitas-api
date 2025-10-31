from __future__ import annotations

from fpdf.enums import XPos, YPos
from app.modules.cloning_report.report.font_config import FontSize

from .base import BaseSectionRenderer


class SummaryPageRenderer(BaseSectionRenderer):
    """Renders the summary (parameters + KPI cards) page."""

    def __post_init__(self) -> None:
        self._kpi_dims: dict[str, float] = {}
        self._kpi_pos: dict[str, float] = {}
        self._kpi_layout: dict[str, float] = {}

    def render(self) -> None:
        self._add_parameters_section()
        self._add_kpi_section()

    def _add_parameters_section(self) -> None:
        pdf = self.pdf
        pdf.add_page()
        pdf.set_font("Helvetica", "B", FontSize.PARAMETERS_SECTION_TITLE)
        pdf.cell(
            0,
            10,
            "Parâmetros de Busca",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(4)
        self._add_parameters_table()

    def _add_parameters_table(self) -> None:
        pdf = self.pdf
        generator = self.generator
        periodo_txt = (
            f"De {generator.periodo_inicio:%d/%m/%Y às %H:%M:%S} "
            f"até {generator.periodo_fim:%d/%m/%Y às %H:%M:%S}"
        )
        suspeita_txt = "Sim" if getattr(generator, "num_suspeitos", 0) > 0 else "Não"
        rows = [
            ("Placa monitorada:", generator.placa),
            ("Marca/Modelo:", getattr(generator, "meta_marca_modelo", "N/A")),
            ("Cor:", getattr(generator, "meta_cor", "N/A")),
            ("Ano Modelo:", str(getattr(generator, "meta_ano_modelo", "N/A"))),
            ("Período analisado:", periodo_txt),
            (
                "Total de pontos detectados:",
                str(getattr(generator, "total_deteccoes", 0)),
            ),
            ("Suspeita de placa clonada:", suspeita_txt),
        ]
        pdf.add_params_table(rows)

    def _add_kpi_section(self) -> None:
        pdf = self.pdf
        pdf.set_font("Helvetica", "B", FontSize.KPI_SECTION_TITLE)
        pdf.cell(
            0,
            10,
            "Quadro Resumo",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(6)
        self._setup_kpi_layout()
        self._add_kpi_boxes()

    def _setup_kpi_layout(self) -> None:
        pdf = self.pdf
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
        y0 = pdf.get_y()
        col_x = [
            pdf.l_margin + i * (box_w + col_gap) for i in range(self._kpi_dims["cols"])
        ]
        self._kpi_pos = {"y0": y0, "col_x": col_x}
        self._kpi_layout = {**self._kpi_dims, **self._kpi_pos}

    def _add_kpi_boxes(self) -> None:
        layout = self._kpi_layout
        pdf = self.pdf
        generator = self.generator

        pdf.add_kpi_box(
            "Número total de registros",
            str(getattr(generator, "total_deteccoes", 0)),
            layout["col_x"][0],
            layout["y0"],
            layout["box_w"],
            layout["row_h1"],
        )

        pdf.add_kpi_box(
            "Número de registros suspeitos",
            str(getattr(generator, "num_suspeitos", 0)),
            layout["col_x"][1],
            layout["y0"],
            layout["box_w"],
            layout["row_h1"],
        )

        dia_txt = getattr(generator, "dia_mais_sus", "N/A")
        if dia_txt != "N/A":
            dia_txt = f"{dia_txt} ({getattr(generator, 'sus_dia_mais_sus', '0')})"

        pdf.add_kpi_box(
            "Dia com mais registros suspeitos",
            dia_txt,
            layout["col_x"][2],
            layout["y0"],
            layout["box_w"],
            layout["row_h1"],
        )
