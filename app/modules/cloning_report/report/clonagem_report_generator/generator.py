from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.modules.cloning_report.analytics import (
    compute_bairro_pair_stats,
    compute_clonagem_kpis,
    plot_bairro_pair_stats,
)
from app.modules.cloning_report.detection.pipeline import DetectionPipeline
from app.modules.cloning_report.detection.preprocessing import DetectionPreprocessor
from app.modules.cloning_report.report import ReportPDF
from app.modules.cloning_report.report.clonagem_report_pdf_mixin import (
    ClonagemReportPDFMixin,
)
from app.modules.cloning_report.utils import ReportPaths


class ClonagemReportGenerator(ClonagemReportPDFMixin):
    """Legacy FPDF generator that prepares cloning report data and delegates rendering to mixins."""

    def __init__(
        self,
        df: pd.DataFrame,
        placa: str,
        periodo_inicio: pd.Timestamp,
        periodo_fim: pd.Timestamp,
        report_id: str | None = None,
    ):
        self.report_id = report_id or self._generate_unique_report_id()
        self._initialize_parameters(df, placa, periodo_inicio, periodo_fim)
        self._initialize_attributes()
        self._report_root_name = ReportPaths.to_directory_name(self.report_id)
        self._is_prepared = False

    # ------------------------------------------------------------------ #
    # Initialisation & data preparation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _generate_unique_report_id() -> str:
        import random

        now = datetime.now()
        return f"{now.strftime('%Y%m%d.%H%M%S')}{random.randint(0, 999):03d}"

    def _initialize_parameters(
        self,
        df: pd.DataFrame,
        placa: str,
        periodo_inicio: pd.Timestamp,
        periodo_fim: pd.Timestamp,
    ) -> None:
        self.df_raw = df
        self.placa = placa
        self.periodo_inicio = periodo_inicio
        self.periodo_fim = periodo_fim

    def _initialize_attributes(self) -> None:
        self.df = pd.DataFrame()
        self.results: dict[str, Any] = {}

    def _setup(self) -> None:
        self._prepare_dataframe()
        self._set_metadata()
        self._run_analysis()
        self._extract_kpis()

    def _prepare_dataframe(self) -> None:
        dfx = DetectionPreprocessor.prepare_dataframe(self.df_raw.copy())
        self.df = dfx[
            (dfx["datahora"] >= self.periodo_inicio)
            & (dfx["datahora"] <= self.periodo_fim)
        ].copy()
        self.total_deteccoes = int(len(self.df))

    def _set_metadata(self) -> None:
        self.meta_marca_modelo = (
            (str(self.df["marca"].iloc[0]) + "/" + str(self.df["modelo"].iloc[0]))
            if {"marca", "modelo"}.issubset(self.df.columns)
            and not self.df[["marca", "modelo"]].isna().any().any()
            else "CHEV/TRACKER 12T A PR"
        )
        self.meta_cor = (
            str(self.df["cor"].iloc[0]).upper()
            if "cor" in self.df.columns and pd.notna(self.df["cor"].iloc[0])
            else "PRETA"
        )
        self.meta_ano_modelo = (
            int(self.df["ano_modelo"].iloc[0])
            if "ano_modelo" in self.df.columns
            and pd.notna(self.df["ano_modelo"].iloc[0])
            else 2021
        )

    def _run_analysis(self) -> None:
        self.results = DetectionPipeline.detect_cloning(self.df, plot=True)

    def _extract_kpis(self) -> None:
        kpis = compute_clonagem_kpis(self.results)
        self._assign_kpi_values(kpis)
        self.bairro_pairs_df = compute_bairro_pair_stats(self.results)
        self.bairro_pairs_png = plot_bairro_pair_stats(self.bairro_pairs_df, top_n=12)

    def _assign_kpi_values(self, kpis: dict[str, Any]) -> None:
        self._assign_basic_kpis(kpis)
        self._assign_advanced_kpis(kpis)

    def _assign_basic_kpis(self, kpis: dict[str, Any]) -> None:
        self.num_suspeitos = kpis["num_suspeitos"]
        self.max_vel = kpis["max_vel"]
        self.dia_mais_sus = kpis["dia_mais_sus"]
        self.sus_dia_mais_sus = kpis["sus_dia_mais_sus"]

    def _assign_advanced_kpis(self, kpis: dict[str, Any]) -> None:
        self._assign_turn_kpis(kpis)
        self._assign_place_kpis(kpis)
        self._assign_pair_kpis(kpis)

    def _assign_turn_kpis(self, kpis: dict[str, Any]) -> None:
        self.turno_mais_sus = kpis["turno_mais_sus"]
        self.turno_mais_sus_count = kpis["turno_mais_sus_count"]

    def _assign_place_kpis(self, kpis: dict[str, Any]) -> None:
        self.place_lider = kpis["place_lider"]
        self.place_lider_count = kpis["place_lider_count"]

    def _assign_pair_kpis(self, kpis: dict[str, Any]) -> None:
        self.top_pair_str = kpis["top_pair_str"]
        self.top_pair_count = kpis["top_pair_count"]

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def generate(self, output_path: str = "report/relatorio_clonagem.pdf") -> str:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not self._is_prepared:
            self._report_root_name = ReportPaths.to_directory_name(output_path.stem)

        with ReportPaths.use_report_root(self._report_root_name):
            self._ensure_prepared()
            pdf = self._create_pdf()
            self._add_all_pages(pdf)  # provided by mixin
            pdf.output(str(output_path))
        return str(output_path)

    def get_suspicious_pairs(self) -> list[dict[str, Any]]:
        with ReportPaths.use_report_root(self._report_root_name):
            self._ensure_prepared()
            df = self.results.get("dataframe", pd.DataFrame())
            return df.to_dict("records") if isinstance(df, pd.DataFrame) else []

    def get_analysis_summary(self) -> dict[str, Any]:
        with ReportPaths.use_report_root(self._report_root_name):
            self._ensure_prepared()
            return {
                "total_detections": getattr(self, "total_deteccoes", 0),
                "suspicious_pairs_count": getattr(self, "num_suspeitos", 0),
                "period_start": self.periodo_inicio.isoformat(),
                "period_end": self.periodo_fim.isoformat(),
                "plate": self.placa,
            }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _create_pdf(self) -> ReportPDF:
        pdf = ReportPDF(report_id=self.report_id)
        self._setup_pdf_fonts(pdf)
        pdf.alias_nb_pages()
        return pdf

    def _setup_pdf_fonts(
        self, pdf: ReportPDF
    ) -> None:  # pragma: no cover - retained for API
        pass

    def _ensure_prepared(self) -> None:
        if self._is_prepared:
            return
        self._setup()
        self._is_prepared = True
