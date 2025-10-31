from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from collections.abc import Iterable

import pandas as pd

from app.modules.cloning_report.maps import (
    generate_trails_map,
    render_overall_map_png,
)
from app.modules.cloning_report.report.clonagem_report_generator.generator import (
    ClonagemReportGenerator,
)
from app.modules.cloning_report.utils import ReportPaths


@dataclass(frozen=True)
class MetadataEntry:
    label: str
    value: str


@dataclass(frozen=True)
class TableData:
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass(frozen=True)
class TrackSectionData:
    title: str
    map_path: str | None
    table: TableData


@dataclass(frozen=True)
class DailySectionData:
    date: str
    map_path: str | None
    table: TableData
    tracks: list[TrackSectionData] = field(default_factory=list)


@dataclass(frozen=True)
class SummaryData:
    total_records: int
    suspicious_records: int
    most_suspicious_day: str
    most_suspicious_day_count: str
    max_speed: float | None
    turn_label: str
    turn_count: int | None
    location_label: str
    location_count: int | None
    top_pair_label: str
    top_pair_count: int | None


@dataclass(frozen=True)
class ClonagemReportData:
    report_id: str
    plate: str
    period_start: datetime
    period_end: datetime
    metadata: list[MetadataEntry]
    summary: SummaryData
    general_map_path: str | None
    general_table: TableData
    bairro_pairs_chart_path: str | None
    daily_sections: list[DailySectionData]
    suspicious_pairs: list[dict[str, Any]]


class ClonagemReportDataBuilder:
    """Build structured data extracted from a prepared ClonagemReportGenerator."""

    GENERAL_TABLE_COLUMNS = ["Data", "Origem", "Destino", "Km", "s", "Km/h"]

    def __init__(self, generator: ClonagemReportGenerator):
        self._generator = generator

    def build(self) -> ClonagemReportData:
        with ReportPaths.use_report_root(self._generator._report_root_name):
            self._generator._ensure_prepared()

            suspeitos = self._get_suspeitos_dataframe()
            general_map_path = self._build_general_map(suspeitos)
            general_table = self._dataframe_to_table(
                suspeitos, self.GENERAL_TABLE_COLUMNS
            )
            daily_sections = self._build_daily_sections(suspeitos)

            data = ClonagemReportData(
                report_id=self._generator.report_id,
                plate=self._generator.placa,
                period_start=self._generator.periodo_inicio.to_pydatetime(),
                period_end=self._generator.periodo_fim.to_pydatetime(),
                metadata=self._build_metadata_entries(),
                summary=self._build_summary_data(),
                general_map_path=general_map_path,
                general_table=general_table,
                bairro_pairs_chart_path=self._safe_path(
                    self._generator.bairro_pairs_png
                ),
                daily_sections=daily_sections,
                suspicious_pairs=self._dataframe_to_records(suspeitos),
            )
            return data

    # --------------------------------------------------------------------- #
    # Builders
    # --------------------------------------------------------------------- #
    def _build_metadata_entries(self) -> list[MetadataEntry]:
        periodo_txt = self._format_period()
        suspeita = "Sim" if getattr(self._generator, "num_suspeitos", 0) > 0 else "Não"

        entries = [
            MetadataEntry("Placa monitorada:", self._generator.placa),
            MetadataEntry(
                "Marca/Modelo:", getattr(self._generator, "meta_marca_modelo", "N/A")
            ),
            MetadataEntry("Cor:", getattr(self._generator, "meta_cor", "N/A")),
            MetadataEntry(
                "Ano Modelo:", str(getattr(self._generator, "meta_ano_modelo", "N/A"))
            ),
            MetadataEntry("Período analisado:", periodo_txt),
            MetadataEntry(
                "Total de pontos detectados:",
                str(getattr(self._generator, "total_deteccoes", 0)),
            ),
            MetadataEntry("Suspeita de placa clonada:", suspeita),
        ]
        return entries

    def _build_summary_data(self) -> SummaryData:
        return SummaryData(
            total_records=int(getattr(self._generator, "total_deteccoes", 0) or 0),
            suspicious_records=int(getattr(self._generator, "num_suspeitos", 0) or 0),
            most_suspicious_day=str(getattr(self._generator, "dia_mais_sus", "N/A")),
            most_suspicious_day_count=str(
                getattr(self._generator, "sus_dia_mais_sus", "0")
            ),
            max_speed=self._as_float(getattr(self._generator, "max_vel", None)),
            turn_label=str(getattr(self._generator, "turno_mais_sus", "N/A")),
            turn_count=self._as_int(
                getattr(self._generator, "turno_mais_sus_count", None)
            ),
            location_label=str(getattr(self._generator, "place_lider", "N/A")),
            location_count=self._as_int(
                getattr(self._generator, "place_lider_count", None)
            ),
            top_pair_label=str(getattr(self._generator, "top_pair_str", "N/A")),
            top_pair_count=self._as_int(
                getattr(self._generator, "top_pair_count", None)
            ),
        )

    def _build_general_map(self, suspeitos: pd.DataFrame) -> str | None:
        if isinstance(suspeitos, pd.DataFrame) and not suspeitos.empty:
            return self._safe_path(render_overall_map_png(suspeitos))
        return None

    def _build_daily_sections(self, suspeitos: pd.DataFrame) -> list[DailySectionData]:
        sections: list[DailySectionData] = []
        daily_figs = self._generator.results.get("daily_figures", []) or []
        if not daily_figs:
            return sections

        daily_tables = self._generator.results.get("daily_tables", {}) or {}
        tracks_by_day = self._generator.results.get("daily_track_tables", {}) or {}

        for fig in sorted(daily_figs, key=lambda item: item.get("date", "")):
            day = fig.get("date")
            if not day:
                continue

            table_df = self._resolve_day_table(day, daily_tables, suspeitos)
            table = self._dataframe_to_table(table_df, self.GENERAL_TABLE_COLUMNS)
            tracks = self._build_track_sections(day, tracks_by_day)

            sections.append(
                DailySectionData(
                    date=day,
                    map_path=self._safe_path(fig.get("path")),
                    table=table,
                    tracks=tracks,
                )
            )

        return sections

    def _build_track_sections(
        self, day: str, tracks_by_day: dict[str, Any]
    ) -> list[TrackSectionData]:
        if not isinstance(tracks_by_day, dict):
            return []

        tracks = tracks_by_day.get(day)
        if not isinstance(tracks, dict):
            return []

        df_carro1 = tracks.get("carro1")
        df_carro2 = tracks.get("carro2")
        track_tables = [
            ("Trilha - Carro 1", df_carro1, "carro1"),
            ("Trilha - Carro 2", df_carro2, "carro2"),
        ]

        pngs: dict[str, str] = {}
        if any(
            isinstance(df, pd.DataFrame) and not df.empty for _, df, _ in track_tables
        ):
            try:
                pngs = generate_trails_map(
                    self._generator.results.get("dataframe", pd.DataFrame()),
                    day,
                    tracks,
                )
            except Exception:
                pngs = {}

        sections: list[TrackSectionData] = []
        for title, df, key in track_tables:
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            sections.append(
                TrackSectionData(
                    title=f"{title} - {day}",
                    map_path=self._safe_path(pngs.get(key)),
                    table=self._dataframe_to_table(df),
                )
            )

        return sections

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #
    def _get_suspeitos_dataframe(self) -> pd.DataFrame:
        suspeitos = self._generator.results.get("dataframe")
        if isinstance(suspeitos, pd.DataFrame):
            return suspeitos.copy()
        return pd.DataFrame()

    def _resolve_day_table(
        self,
        day: str,
        daily_tables: dict[str, dict[str, pd.DataFrame]],
        suspeitos: pd.DataFrame,
    ) -> pd.DataFrame:
        from pandas import DataFrame

        if (
            isinstance(daily_tables, dict)
            and day in daily_tables
            and isinstance(daily_tables[day], dict)
        ):
            table = daily_tables[day].get("todas")
            if isinstance(table, DataFrame):
                return table

        if not isinstance(suspeitos, pd.DataFrame) or suspeitos.empty:
            return pd.DataFrame(columns=self.GENERAL_TABLE_COLUMNS)

        df_tmp = suspeitos.copy()
        dt = pd.to_datetime(df_tmp["Data"], errors="coerce")
        mask = dt.dt.strftime("%d/%m/%Y") == day
        columns = [c for c in self.GENERAL_TABLE_COLUMNS if c in df_tmp.columns]
        filtered = df_tmp.loc[mask, columns]
        return filtered.reset_index(drop=True)

    @staticmethod
    def _dataframe_to_table(
        df: pd.DataFrame | None, columns: Iterable[str] | None = None
    ) -> TableData:
        if not isinstance(df, pd.DataFrame) or df.empty:
            return TableData(headers=list(columns or []), rows=[])

        if columns:
            available = [col for col in columns if col in df.columns]
            df_sel = df[available].copy()
        else:
            available = list(df.columns)
            df_sel = df.copy()

        df_sel = df_sel.fillna("")

        rows: list[list[str]] = []
        for record in df_sel.to_dict(orient="records"):
            row = []
            for col in available:
                value = record.get(col, "")
                row.append(ClonagemReportDataBuilder._format_cell(value))
            rows.append(row)

        return TableData(headers=available, rows=rows)

    @staticmethod
    def _dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
        if not isinstance(df, pd.DataFrame) or df.empty:
            return []
        return df.fillna("").to_dict(orient="records")

    def _format_period(self) -> str:
        inicio = self._generator.periodo_inicio
        fim = self._generator.periodo_fim
        return (
            f"De {inicio:%d/%m/%Y às %H:%M:%S} até {fim:%d/%m/%Y às %H:%M:%S}"
            if inicio and fim
            else "Período não informado"
        )

    @staticmethod
    def _format_cell(value: Any) -> str:
        if isinstance(value, float):
            if pd.isna(value):
                return ""
            if float(value).is_integer():
                return str(int(value))
            return f"{value:.2f}"
        if isinstance(value, pd.Timestamp):
            return value.strftime("%d/%m/%Y %H:%M:%S")
        return str(value)

    @staticmethod
    def _safe_path(path: Any) -> str | None:
        if not path:
            return None
        return str(path)

    @staticmethod
    def _as_float(value: Any) -> float | None:
        try:
            if value in ("", None):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_int(value: Any) -> int | None:
        try:
            if value in ("", None):
                return None
            return int(value)
        except (TypeError, ValueError):
            return None
