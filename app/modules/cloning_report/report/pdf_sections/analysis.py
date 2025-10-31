from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import pandas as pd

from app.modules.cloning_report.maps import render_overall_map_png, generate_trails_map

from .base import BaseSectionRenderer
from .instructions import InstructionsPageRenderer


class CloningAnalysisRenderer(BaseSectionRenderer):
    """Renders the cloning-analysis section (maps, tables, daily details)."""

    def render(self) -> None:
        self._add_cloning_title()
        self._add_general_analysis()
        self._add_daily_analysis()

    # --- section title & overview -----------------------------------------
    def _add_cloning_title(self) -> None:
        pdf = self.pdf
        pdf.add_page()
        pdf.chapter_title("1. Análise de Possíveis Sinais de Clonagem")

    def _add_general_analysis(self) -> None:
        suspeitos = self._suspeitos_df
        if isinstance(suspeitos, pd.DataFrame) and not suspeitos.empty:
            InstructionsPageRenderer(self.generator, self.pdf).render_methodology_only()
            self._add_general_map_section(suspeitos)
            self._add_general_table_section(suspeitos)
        else:
            self._add_no_suspicious_records_message()

    @property
    def _suspeitos_df(self) -> pd.DataFrame:
        suspeitos = self.generator.results.get("dataframe", pd.DataFrame())
        return suspeitos if isinstance(suspeitos, pd.DataFrame) else pd.DataFrame()

    def _add_general_map_section(self, suspeitos: pd.DataFrame) -> None:
        pdf = self.pdf
        pdf.add_page()
        pdf.sub_title("1.1 Mapa geral do período - todas as detecções suspeitas")
        png_all = render_overall_map_png(suspeitos)
        if png_all:
            pdf.add_figure(png_all, title="", text=None, width_factor=0.98)
        else:
            pdf.chapter_body("Não há registros suspeitos para exibir no mapa geral.")

    def _add_general_table_section(self, suspeitos: pd.DataFrame) -> None:
        pdf = self.pdf
        table_text = (
            "A tabela apresenta os registros suspeitos identificados no período. "
            "Ela mostra Data (primeira detecção), Primeira Detecção (local e radar), "
            "Detecção Seguinte (local e radar) e a velocidade média."
        )
        pdf.add_table(
            suspeitos[["Data", "Origem", "Destino", "Km", "s", "Km/h"]],
            title="1.2 Tabela geral de detecções suspeitas",
            text=table_text,
        )

    def _add_no_suspicious_records_message(self) -> None:
        pdf = self.pdf
        pdf.chapter_body(
            "Não foram identificados registros suspeitos no período informado. "
            "Caso existam poucos registros no intervalo, experimente ampliar o período."
        )

    # --- daily analysis ---------------------------------------------------
    def _add_daily_analysis(self) -> None:
        daily_figs = self.generator.results.get("daily_figures", [])
        if not daily_figs:
            return
        self._setup_daily_analysis()
        self._process_daily_figures(daily_figs)

    def _setup_daily_analysis(self) -> None:
        pdf = self.pdf
        pdf.add_page()
        pdf.chapter_title("2. Registros e Mapas Diários")

    def _process_daily_figures(self, daily_figs: list[dict[str, str]]) -> None:
        daily_tables = self.generator.results.get("daily_tables", {}) or {}
        tracks_by_day = self.generator.results.get("daily_track_tables", {}) or {}
        df_sus = self._suspeitos_df

        sorted_figs = sorted(
            daily_figs, key=lambda x: datetime.strptime(x["date"], "%d/%m/%Y")
        )
        for idx, item in enumerate(sorted_figs):
            if idx != 0:
                self.pdf.add_page()
            self._render_single_day(item, daily_tables, tracks_by_day, df_sus)

    def _render_single_day(
        self,
        item: dict[str, str],
        daily_tables: dict[str, dict[str, pd.DataFrame]],
        tracks_by_day: dict[str, Any],
        df_sus: pd.DataFrame,
    ) -> None:
        day_key = item["date"]
        pdf = self.pdf
        pdf.add_figure(
            item["path"], f"Mapa do dia de registros suspeitos - {day_key}", text=None
        )

        df_day = self._get_day_data(daily_tables, day_key, df_sus)
        if df_day is not None and not df_day.empty:
            self._add_day_table(df_day, day_key)
            self._add_day_tracks(day_key, tracks_by_day, df_day)
        else:
            pdf.chapter_body("Sem registros suspeitos para tabular neste dia.")

    def _get_day_data(
        self,
        daily_tables: dict[str, dict[str, pd.DataFrame]],
        day_key: str,
        df_sus: pd.DataFrame,
    ) -> pd.DataFrame:
        if (
            isinstance(daily_tables, dict)
            and day_key in daily_tables
            and isinstance(daily_tables[day_key], dict)
        ):
            table = daily_tables[day_key].get("todas")
            if isinstance(table, pd.DataFrame):
                return table

        if not df_sus.empty:
            df_tmp = df_sus.copy()
            dt = pd.to_datetime(df_tmp["Data"], errors="coerce")
            mask = dt.dt.strftime("%d/%m/%Y") == day_key
            cols = ["Data", "Origem", "Destino", "Km", "s", "Km/h"]
            filtered = df_tmp.loc[mask, cols]
            return filtered.reset_index(drop=True)

        return pd.DataFrame(columns=["Data", "Origem", "Destino", "Km", "s", "Km/h"])

    def _add_day_table(self, df_day: pd.DataFrame, day_key: str) -> None:
        pdf = self.pdf
        try:
            df_print = df_day.copy()
            df_print["Km/h"] = pd.to_numeric(df_print["Km/h"], errors="coerce")
        except Exception:
            df_print = df_day

        pdf.add_table(
            df_print[["Data", "Origem", "Destino", "Km", "s", "Km/h"]],
            title=f"Registros suspeitos do dia - {day_key}",
            text=None,
        )

    def _add_day_tracks(
        self,
        day_key: str,
        tracks_by_day: dict[str, Any],
        df_day: pd.DataFrame,
    ) -> None:
        tracks = tracks_by_day.get(day_key) if isinstance(tracks_by_day, dict) else None
        df_c1, df_c2 = self._get_track_dataframes(tracks)
        tem_trilhas = self._check_tracks_exist(df_c1, df_c2)

        single_pair_with_tracks = (
            df_day is not None and len(df_day) == 1 and tem_trilhas
        )

        if single_pair_with_tracks:
            self._add_single_pair_tracks(df_c1, df_c2, day_key)
        elif tem_trilhas:
            self._add_multiple_tracks(day_key, tracks, df_c1, df_c2)

    @staticmethod
    def _get_track_dataframes(
        tracks: dict[str, Any] | None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        df_c1 = tracks.get("carro1", pd.DataFrame()) if tracks else pd.DataFrame()
        df_c2 = tracks.get("carro2", pd.DataFrame()) if tracks else pd.DataFrame()
        return df_c1, df_c2

    @staticmethod
    def _check_tracks_exist(df_c1: pd.DataFrame, df_c2: pd.DataFrame) -> bool:
        return (
            isinstance(df_c1, pd.DataFrame)
            and not df_c1.empty
            and isinstance(df_c2, pd.DataFrame)
            and not df_c2.empty
        )

    def _add_single_pair_tracks(
        self,
        df_c1: pd.DataFrame,
        df_c2: pd.DataFrame,
        day_key: str,
    ) -> None:
        pdf = self.pdf
        pdf.add_table(df_c1, title=f"Tabela da trilha - Carro 1 - {day_key}")
        pdf.add_table(df_c2, title=f"Tabela da trilha - Carro 2 - {day_key}")

    def _add_multiple_tracks(
        self,
        day_key: str,
        tracks: dict[str, Any] | None,
        df_c1: pd.DataFrame,
        df_c2: pd.DataFrame,
    ) -> None:
        pdf = self.pdf
        pdf.add_page()
        pdf.sub_title(f"Trilhas (clusters) - {day_key}")

        pngs = self._generate_trail_maps(day_key, tracks)

        if not df_c1.empty:
            self._add_car_track(df_c1, pngs, "carro1", day_key, "Carro 1")

        if not df_c2.empty:
            self._add_car_track(df_c2, pngs, "carro2", day_key, "Carro 2")

    def _generate_trail_maps(
        self,
        day_key: str,
        tracks: dict[str, Any] | None,
    ) -> dict[str, str]:
        if not tracks:
            return {}
        try:
            return generate_trails_map(self._suspeitos_df, day_key, tracks)
        except Exception:
            return {}

    def _add_car_track(
        self,
        df_car: pd.DataFrame,
        pngs: dict[str, str],
        key: str,
        day_key: str,
        label: str,
    ) -> None:
        pdf = self.pdf
        if key in pngs and os.path.exists(pngs[key]):
            pdf.image(pngs[key], x=10, y=None, w=190)
        pdf.add_table(df_car, title=f"Tabela da trilha - {label} - {day_key}")
