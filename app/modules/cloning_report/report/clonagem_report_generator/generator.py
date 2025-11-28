from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Any

import pandas as pd
from fpdf.enums import XPos, YPos
from app.modules.cloning_report.detection.preprocessing import DetectionPreprocessor
from app.modules.cloning_report.detection.pipeline import DetectionPipeline
from app.modules.cloning_report.analytics import (
    compute_clonagem_kpis,
    compute_bairro_pair_stats,
    plot_bairro_pair_stats,
)
from app.modules.cloning_report.maps import render_overall_map_png, generate_trails_map
from app.modules.cloning_report.report import ReportPDF
from app.modules.cloning_report.report.clonagem_report_generator.instructions_builder_manual import (
    InstructionsBuilderManual,
)
from app.modules.cloning_report.report.font_config import FontSize
from app.modules.cloning_report.utils import strftime_safe
from app.modules.cloning_report.utils.archive import create_report_temp_dir
from app.modules.cloning_report.report.clonagem_report_generator.kpi_box_builder import (
    KpiBoxBuilder,
)
from app.modules.cloning_report.utils.filesystem import FileSystemService


# =========================================================
# GERADOR - estrutura com KPIs de clonagem
# =========================================================
class ClonagemReportGenerator(KpiBoxBuilder, InstructionsBuilderManual):
    DATETIME_DISPLAY_FORMAT = "%d/%m/%Y %H:%M:%S"

    def __init__(
        self,
        df: pd.DataFrame,
        placa: str,
        periodo_inicio: pd.Timestamp,
        periodo_fim: pd.Timestamp,
        report_id: str = None,
    ):
        self.report_id = report_id or self._generate_unique_report_id()
        self._initialize_parameters(df, placa, periodo_inicio, periodo_fim)
        self._initialize_attributes()
        self._setup_done = False

    # ---------- geração ----------
    def generate(self, output_path: str | Path | None = None):
        token = FileSystemService.set_report_context(self.report_id)
        try:
            if not self._setup_done:
                self._setup()
                self._setup_done = True

            if output_path is None:
                base_dir = create_report_temp_dir(self.report_id)
                file_name = (
                    f"relatorio_clonagem_{self.placa}_"
                    f"{self.periodo_inicio.strftime('%Y%m%d')}_"
                    f"{self.periodo_fim.strftime('%Y%m%d')}.pdf"
                )
                output_path = base_dir / file_name
            else:
                output_path = Path(output_path)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            pdf = self._create_pdf()
            self._add_all_pages(pdf)
            pdf.output(str(output_path))
            return output_path
        finally:
            try:
                FileSystemService.reset_report_context(token)
            except Exception:
                # ignore TokenErrors from cross-context usage; context is best-effort
                pass

    def _generate_unique_report_id(self):
        """Generate unique report ID"""
        import random
        from datetime import datetime

        now = datetime.now()
        return f"{now.strftime('%Y%m%d.%H%M%S')}{random.randint(0, 999):03d}"

    def _initialize_parameters(
        self,
        df: pd.DataFrame,
        placa: str,
        periodo_inicio: pd.Timestamp,
        periodo_fim: pd.Timestamp,
    ):
        self.df_raw = df
        self.placa = placa
        self.periodo_inicio = periodo_inicio
        self.periodo_fim = periodo_fim

    def _initialize_attributes(self):
        self.df = pd.DataFrame()
        self.results: dict[str, Any] = {}

    # ---------- preparação ----------
    def _setup(self):
        self._prepare_dataframe()
        # self._set_metadata()
        self._run_analysis()
        self._extract_kpis()

    def _prepare_dataframe(self):
        dfx = DetectionPreprocessor.prepare_dataframe(self.df_raw.copy())
        self.df = dfx[
            (dfx["datahora"] >= self.periodo_inicio)
            & (dfx["datahora"] <= self.periodo_fim)
        ].copy()
        self.total_deteccoes = int(len(self.df))

    def _run_analysis(self):
        self.results = DetectionPipeline.detect_cloning(self.df, plot=True)

    def _extract_kpis(self):
        k = compute_clonagem_kpis(self.results)
        self._assign_basic_kpis(k)
        self.bairro_pairs_df = compute_bairro_pair_stats(self.results)
        self.bairro_pairs_png = plot_bairro_pair_stats(self.bairro_pairs_df, top_n=12)

    def _assign_basic_kpis(self, k):
        self.num_suspeitos = k["num_suspeitos"]
        self.max_vel = k["max_vel"]
        self.dia_mais_sus = k["dia_mais_sus"]
        self.sus_dia_mais_sus = k["sus_dia_mais_sus"]

    # =====================================================
    # Páginas
    # =====================================================
    def _add_instructions_page(self, pdf):
        self._add_title_section(pdf)
        self.render_static_content_first(pdf)

    def _add_all_pages(self, pdf):
        self._add_instructions_page(pdf)
        self._add_kpi_section(pdf)
        self.render_static_content_second(pdf)
        self._add_cloning_section(pdf)

    def _add_title_section(self, pdf):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", FontSize.MAIN_TITLE)
        pdf.cell(
            0,
            10,
            "Relatório de Suspeita de Clonagem de Placa",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="C",
        )
        pdf.ln(5)

    def _add_kpi_section(self, pdf: ReportPDF):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(
            pdf.epw, 5, "Quadro Resumo", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L"
        )
        pdf.ln(6)
        self._add_kpi_boxes(pdf)

    def _add_kpi_boxes(self, pdf: ReportPDF):
        self.setup_kpi_layout(pdf)
        self.add_kpi_boxes_content(pdf)

    def _add_cloning_section(self, pdf: ReportPDF):
        suspeitos = self.results.get("dataframe", pd.DataFrame())
        daily_figs = self.results.get("daily_figures", [])
        pdf.chapter_title("1. Análise de Possíveis Sinais de Clonagem")
        self._add_general_analysis(pdf, suspeitos)
        self._add_daily_analysis(pdf, daily_figs, suspeitos)

    def _add_general_analysis(self, pdf: ReportPDF, suspeitos):
        if isinstance(suspeitos, pd.DataFrame) and not suspeitos.empty:
            self._add_general_map_section(pdf, suspeitos)
            self._add_general_table_section(pdf, suspeitos)
        else:
            self._add_no_suspicious_records_message(pdf)

    def _add_general_map_section(self, pdf: ReportPDF, suspeitos):
        if isinstance(suspeitos, pd.DataFrame) and not suspeitos.empty:
            png_all = render_overall_map_png(suspeitos)
            if png_all:
                pdf.add_figure(
                    png_all,
                    title="1.1 Mapa geral do período - todas as detecções suspeitas",
                    text=None,
                    width_factor=0.98,
                )
        else:
            pdf.chapter_body("Não há registros suspeitos para exibir no mapa geral.")

    def _add_general_table_section(self, pdf: ReportPDF, suspeitos):
        if not isinstance(suspeitos, pd.DataFrame) or suspeitos.empty:
            self._add_no_suspicious_records_message(pdf)
            return

        table_df = self._format_datetime_columns(
            suspeitos, ["Data", "DataDestino", "DataFormatada"]
        )
        table_text = (
            "A tabela apresenta os registros suspeitos identificados no período. "
            "Ela mostra Data (primeira detecção), Primeira Detecção (local e radar), "
            "Detecção Seguinte (local e radar) e a velocidade média."
        )
        pdf.add_table(
            table_df[["Data", "Origem", "Destino", "Km", "s", "Km/h"]],
            title="1.2 Tabela geral de detecções suspeitas",
            text=table_text,
        )

    def _add_no_suspicious_records_message(self, pdf: ReportPDF):
        pdf.chapter_body(
            "Não foram identificados registros suspeitos no período informado. "
            "Caso existam poucos registros no intervalo, experimente ampliar o período."
        )

    def _add_daily_analysis(self, pdf: ReportPDF, daily_figs, suspeitos):
        if daily_figs:
            self._setup_daily_analysis(pdf)
            self._process_daily_figures(pdf, daily_figs, suspeitos)

    def _setup_daily_analysis(self, pdf: ReportPDF):
        pdf.add_page()
        pdf.chapter_title("2. Registros e Mapas Diários")

    def _process_daily_figures(self, pdf: ReportPDF, daily_figs, suspeitos):
        daily_tables = self.results.get("daily_tables", {})
        tracks_by_day = self.results.get("daily_track_tables", {})
        df_sus_all = (
            suspeitos if isinstance(suspeitos, pd.DataFrame) else pd.DataFrame()
        )

        sorted_figs = sorted(
            daily_figs, key=lambda x: datetime.strptime(x["date"], "%d/%m/%Y")
        )
        for i, item in enumerate(sorted_figs):
            self._process_single_day(
                pdf, i, item, daily_tables, tracks_by_day, df_sus_all
            )

    def _process_single_day(
        self, pdf: ReportPDF, i, item, daily_tables, tracks_by_day, df_sus_all
    ):
        if i != 0:
            pdf.add_page()

        day_key = item["date"]
        self._add_day_map(pdf, item, day_key)
        df_day = self._get_day_data(daily_tables, day_key, df_sus_all)

        if df_day is not None and not df_day.empty:
            self._add_day_table(pdf, df_day, day_key)
            self._add_day_tracks(pdf, day_key, tracks_by_day, df_day)
        else:
            pdf.chapter_body("Sem registros suspeitos para tabular neste dia.")

    def _add_day_map(self, pdf: ReportPDF, item, day_key):
        titulo = f"Mapa do dia de registros suspeitos - {day_key}"
        pdf.add_figure(item["path"], titulo, text=None)

    def _get_day_data(self, daily_tables, day_key, df_sus_all):
        df_day = None
        if isinstance(daily_tables, dict) and day_key in daily_tables:
            df_day = daily_tables[day_key].get("todas")

        if (
            (df_day is None or df_day.empty)
            and isinstance(df_sus_all, pd.DataFrame)
            and not df_sus_all.empty
        ):
            df_day = self._extract_day_from_suspeitos(df_sus_all, day_key)

        return df_day

    def _extract_day_from_suspeitos(self, df_sus_all, day_key):
        df_tmp = df_sus_all.copy()
        dt = pd.to_datetime(df_tmp["Data"], errors="coerce")
        mask = dt.dt.strftime("%d/%m/%Y") == day_key
        cols = ["Data", "Origem", "Destino", "Km", "s", "Km/h"]
        subset = df_tmp.loc[mask, cols] if mask.any() else pd.DataFrame(columns=cols)
        if subset.empty:
            return subset
        return self._format_datetime_columns(subset, ["Data", "DataDestino"])

    def _add_day_table(self, pdf: ReportPDF, df_day, day_key):
        try:
            df_print = df_day.copy()
            df_print["Km/h"] = pd.to_numeric(df_print["Km/h"], errors="coerce")
        except Exception:
            df_print = df_day
        df_print = self._format_datetime_columns(
            df_print, ["Data", "DataDestino", "DataFormatada"]
        )

        pdf.add_table(
            df_print[["Data", "Origem", "Destino", "Km", "s", "Km/h"]],
            title=f"Registros suspeitos do dia - {day_key}",
            text=None,
        )

    def _add_day_tracks(self, pdf: ReportPDF, day_key, tracks_by_day, df_day):
        tracks = tracks_by_day.get(day_key) if isinstance(tracks_by_day, dict) else None
        df_c1, df_c2 = self._get_track_dataframes(tracks)
        tem_trilhas = self._check_tracks_exist(df_c1, df_c2)

        single_pair_with_tracks = (
            df_day is not None and len(df_day) == 1 and tem_trilhas
        )

        if single_pair_with_tracks:
            self._add_single_pair_tracks(pdf, df_c1, df_c2, day_key)
        elif tem_trilhas:
            self._add_multiple_tracks(pdf, day_key, tracks, df_c1, df_c2)

    def _get_track_dataframes(self, tracks):
        df_c1 = tracks.get("carro1", pd.DataFrame()) if tracks else pd.DataFrame()
        df_c2 = tracks.get("carro2", pd.DataFrame()) if tracks else pd.DataFrame()
        return df_c1, df_c2

    def _check_tracks_exist(self, df_c1, df_c2):
        return (
            isinstance(df_c1, pd.DataFrame)
            and not df_c1.empty
            and isinstance(df_c2, pd.DataFrame)
            and not df_c2.empty
        )

    def _add_single_pair_tracks(self, pdf: ReportPDF, df_c1, df_c2, day_key):
        df_c1_fmt = self._format_datetime_columns(
            df_c1, ["Data", "DataDestino", "DataHora", "DataHora_str"]
        )
        df_c2_fmt = self._format_datetime_columns(
            df_c2, ["Data", "DataDestino", "DataHora", "DataHora_str"]
        )
        pdf.add_table(df_c1_fmt, title=f"Tabela da trilha - Carro 1 - {day_key}")
        pdf.add_table(df_c2_fmt, title=f"Tabela da trilha - Carro 2 - {day_key}")

    def _add_multiple_tracks(self, pdf: ReportPDF, day_key, tracks, df_c1, df_c2):
        pdf.add_page()
        pdf.sub_title(f"Trilhas (clusters) - {day_key}")

        pngs = self._generate_trail_maps(day_key, tracks)

        if not df_c1.empty:
            self._add_car1_track(pdf, pngs, df_c1, day_key)

        if not df_c2.empty:
            self._add_car2_track(pdf, pngs, df_c2, day_key)

    def _generate_trail_maps(self, day_key, tracks) -> dict[str, str | None] | dict:
        try:
            return generate_trails_map(self.results["dataframe"], day_key, tracks)
        except Exception:
            return {}

    def _add_car1_track(self, pdf: ReportPDF, pngs, df_c1, day_key):
        pdf.sub_title(f"Mapa da trilha - Carro 1 - {day_key}")
        if "carro1" in pngs and os.path.exists(pngs["carro1"]):
            pdf.image(pngs["carro1"], x=10, y=None, w=190)
        df_c1_fmt = self._format_datetime_columns(
            df_c1, ["Data", "DataDestino", "DataHora", "DataHora_str"]
        )
        pdf.add_table(df_c1_fmt, title=f"Tabela da trilha - Carro 1 - {day_key}")

    def _add_car2_track(self, pdf: ReportPDF, pngs, df_c2, day_key):
        pdf.add_page()
        pdf.sub_title(f"Mapa da trilha - Carro 2 - {day_key}")
        if "carro2" in pngs and os.path.exists(pngs["carro2"]):
            pdf.image(pngs["carro2"], x=10, y=None, w=190)
        df_c2_fmt = self._format_datetime_columns(
            df_c2, ["Data", "DataDestino", "DataHora", "DataHora_str"]
        )
        pdf.add_table(df_c2_fmt, title=f"Tabela da trilha - Carro 2 - {day_key}")

    def _format_datetime_columns(
        self, df: pd.DataFrame, columns: list[str]
    ) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        formatted = df.copy()
        for col in columns:
            if col in formatted.columns:
                formatted[col] = formatted[col].apply(
                    lambda value: strftime_safe(value, self.DATETIME_DISPLAY_FORMAT)
                )
        return formatted

    def get_suspicious_pairs(self):
        """Get suspicious pairs data"""
        return self.results.get("dataframe", pd.DataFrame()).to_dict("records")

    def _create_pdf(self):
        pdf = ReportPDF(report_id=self.report_id)
        pdf.alias_nb_pages()
        return pdf
