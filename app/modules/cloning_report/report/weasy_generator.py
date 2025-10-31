"""WeasyPrint implementation of the cloning report generator."""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app import config
from app.modules.cloning_report.maps import render_overall_map_png
from app.modules.cloning_report.report.clonagem_report_generator import (
    ClonagemReportGenerator,
)
from app.utils import generate_pdf_report_from_html_template


class ClonagemReportWeasyGenerator(ClonagemReportGenerator):
    """Generate the cloning report using HTML templates rendered via WeasyPrint."""

    TEMPLATE_PATH = "pdf/cloning_report_weasy.html"

    def generate(self, output_path: str = "report/relatorio_clonagem_weasy.pdf") -> str:
        """Render the report to PDF using WeasyPrint."""
        context = self._build_template_context()

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        tmp_pdf = Path(
            generate_pdf_report_from_html_template(context, self.TEMPLATE_PATH)
        )
        shutil.copy(tmp_pdf, output_path)
        tmp_pdf.unlink(missing_ok=True)
        return output_path

    # --------------------------------------------------------------------- #
    # Context builders
    # --------------------------------------------------------------------- #
    def _build_template_context(self) -> dict[str, Any]:
        suspeitos = self.results.get("dataframe", pd.DataFrame())
        daily_figs = self.results.get("daily_figures", []) or []

        general_map_path = None
        if isinstance(suspeitos, pd.DataFrame) and not suspeitos.empty:
            general_map_path = self._safe_path(render_overall_map_png(suspeitos))

        general_table = self._build_table_data(
            suspeitos, ["Data", "Origem", "Destino", "Km", "s", "Km/h"]
        )
        metadata_rows = self._build_metadata_rows()
        kpi_cards = self._build_kpi_cards()
        daily_sections = self._build_daily_sections(daily_figs, suspeitos)
        bairro_pairs_chart = self._safe_path(getattr(self, "bairro_pairs_png", None))
        summary_stats = self._build_summary_stats()
        analysis_highlights = self._build_analysis_highlights()
        icon_paths = self._build_icon_paths()
        example_images = self._build_example_images()
        detection_summary = self._build_detection_summary(general_table)

        context = {
            "report_title": "RELATÓRIO DE SUSPEITA DE CLONAGEM",
            "report_id": self.report_id,
            "plate": self.placa,
            "analysis_period_text": self._format_analysis_period(),
            "time_interval_text": self._format_analysis_period(),
            "metadata_rows": metadata_rows,
            "kpi_cards": kpi_cards,
            "summary_stats": summary_stats,
            "analysis_highlights": analysis_highlights,
            "general_map_path": general_map_path,
            "general_table": general_table,
            "general_table_note": self._general_table_note(),
            "has_suspicious_records": bool(general_table["rows"]),
            "daily_sections": daily_sections,
            "has_daily_sections": any(
                section["map_path"] or section["has_table"] or section["has_tracks"]
                for section in daily_sections
            ),
            "bairro_pairs_chart_path": bairro_pairs_chart,
            "has_bairro_pairs_chart": bool(bairro_pairs_chart),
            "icon_paths": icon_paths,
            "example_images": example_images,
        }

        # Maintain backwards compatibility with the current HTML template expectations
        context.update(
            {
                "time_interval_str": context["time_interval_text"],
                "readings_count": summary_stats["total_records"],
                "suspicious_readings_count": summary_stats["suspicious_records"],
                "most_suspicious_day": summary_stats["most_suspicious_day"],
                "most_suspicious_day_count": summary_stats["most_suspicious_day_count"],
                "icon_radar_path": icon_paths.get("radar"),
                "icon_warning_path": icon_paths.get("warning"),
                "icon_calendar_path": icon_paths.get("calendar"),
                "example_splitable_pair_figure_path": example_images.get("separable"),
                "example_non_splitable_pair_figure_path": example_images.get(
                    "non_separable"
                ),
                "icon_clock_path": icon_paths.get("clock"),
                "icon_location_path": icon_paths.get("location"),
                "icon_speed_path": icon_paths.get("speed"),
                "grafo_limited_nodes_path": self._resolve_grafo_path(
                    bairro_pairs_chart
                ),
                "turno_summary": self._format_value_with_count(
                    getattr(self, "turno_mais_sus", "N/A"),
                    getattr(self, "turno_mais_sus_count", None),
                ),
                "place_summary": self._format_value_with_count(
                    getattr(self, "place_lider", "N/A"),
                    getattr(self, "place_lider_count", None),
                ),
                "top_pair_summary": self._format_value_with_count(
                    getattr(self, "top_pair_str", "N/A"),
                    getattr(self, "top_pair_count", None),
                ),
                "max_speed_summary": self._format_speed(getattr(self, "max_vel", None)),
                "total_monitored_plates": str(len(detection_summary)),
                "detections": detection_summary,
            }
        )

        return context

    def _build_summary_stats(self) -> dict[str, str]:
        total_records = getattr(self, "total_deteccoes", 0) or 0
        suspicious_records = getattr(self, "num_suspeitos", 0) or 0
        most_suspicious_day = getattr(self, "dia_mais_sus", "N/A") or "N/A"
        most_suspicious_day_count = getattr(self, "sus_dia_mais_sus", "0") or "0"

        return {
            "total_records": str(total_records),
            "suspicious_records": str(suspicious_records),
            "most_suspicious_day": str(most_suspicious_day),
            "most_suspicious_day_count": str(most_suspicious_day_count),
        }

    def _build_analysis_highlights(self) -> list[dict[str, str]]:
        highlights: list[dict[str, str]] = []

        def add_entry(label: str, base_value: Any, count: Any | None = None):
            if base_value in (None, "", "N/A"):
                value = "N/A"
            else:
                value = str(base_value)
                if count not in (None, "", 0, "0"):
                    value = f"{value} ({count})"
            highlights.append({"label": label, "value": value})

        add_entry(
            "Turno com mais registros suspeitos",
            getattr(self, "turno_mais_sus", "N/A"),
            getattr(self, "turno_mais_sus_count", None),
        )
        add_entry(
            "Local com mais ocorrências suspeitas",
            getattr(self, "place_lider", "N/A"),
            getattr(self, "place_lider_count", None),
        )
        add_entry(
            "Par de radares mais frequente entre os suspeitos",
            getattr(self, "top_pair_str", "N/A"),
            getattr(self, "top_pair_count", None),
        )

        return highlights

    def _build_icon_paths(self) -> dict[str, str]:
        assets_root = Path(config.ASSETS_DIR) / "cloning_report"
        icon_map = {
            "radar": "radar.png",
            "warning": "warning.png",
            "calendar": "calendar.png",
            "clock": "clock.png",
            "location": "location.png",
            "speed": "car-speed.png",
        }
        return {
            name: self._safe_path(assets_root / filename)
            for name, filename in icon_map.items()
        }

    def _build_example_images(self) -> dict[str, str | None]:
        figs_root = Path(config.ASSETS_DIR) / "cloning_report" / "figs"
        return {
            "separable": self._safe_path(figs_root / "par_separavel.jpeg"),
            "non_separable": self._safe_path(figs_root / "par_nao_separavel.png"),
        }

    def _resolve_grafo_path(self, generated_chart: str | None) -> str | None:
        """
        Resolve the path for the relationship graph image. Prefer dynamically generated
        assets (e.g. from analytics plots) and fall back to a static asset when unavailable.
        """
        if generated_chart:
            return generated_chart

        fallback = Path(config.ASSETS_DIR) / "cloning_report" / "bairro_pairs_top.png"
        return self._safe_path(fallback)

    def _build_detection_summary(
        self, general_table: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Build the collection of suspicious detection records expected by the template.
        Mirrors the legacy FPDF table (Data, Origem, Destino, Km, s, Km/h).
        """
        rows = general_table.get("rows") or []
        headers = general_table.get("headers") or []
        if not rows or not headers:
            return []

        header_map = {
            "Data": "data",
            "Origem": "origem",
            "Destino": "destino",
            "Km": "km",
            "s": "seconds",
            "Km/h": "kmh",
        }

        records: list[dict[str, Any]] = []
        for row in rows:
            record: dict[str, Any] = {}
            for header, value in zip(headers, row):
                key = header_map.get(header)
                if key:
                    record[key] = value
            records.append(record)
        return records

    @staticmethod
    def _format_value_with_count(value: Any, count: Any | None) -> str:
        if value in (None, "", "N/A"):
            return "N/A"
        base = str(value)
        if count in (None, "", "0", 0):
            return base
        return f"{base} ({count})"

    @staticmethod
    def _format_speed(value: Any) -> str:
        if value in (None, "", "N/A"):
            return "N/A"
        try:
            return f"{float(value):.2f} km/h"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _general_table_note() -> str:
        return (
            "A tabela apresenta os registros suspeitos identificados no período. "
            "Ela mostra Data (primeira detecção), Origem (local e radar), Destino (local e radar) "
            "e a velocidade média estimada entre os pontos analisados."
        )

    def _safe_path(self, path: Any) -> str | None:
        if path in (None, "", False):
            return None
        try:
            path_obj = Path(path)
        except (TypeError, ValueError):
            try:
                return str(path)
            except Exception:
                return None
        return path_obj.as_posix()

    def _build_metadata_rows(self) -> list[dict[str, str]]:
        periodo_txt = self._format_analysis_period()
        suspeita_txt = "Sim" if getattr(self, "num_suspeitos", 0) > 0 else "Não"

        return [
            {"label": "Placa monitorada:", "value": self.placa},
            {
                "label": "Marca/Modelo:",
                "value": getattr(self, "meta_marca_modelo", "N/A"),
            },
            {"label": "Cor:", "value": getattr(self, "meta_cor", "N/A")},
            {
                "label": "Ano Modelo:",
                "value": str(getattr(self, "meta_ano_modelo", "N/A")),
            },
            {"label": "Período analisado:", "value": periodo_txt},
            {
                "label": "Total de pontos detectados:",
                "value": str(getattr(self, "total_deteccoes", 0)),
            },
            {"label": "Suspeita de placa clonada:", "value": suspeita_txt},
        ]

    def _build_kpi_cards(self) -> list[dict[str, str]]:
        num_suspeitos = getattr(self, "num_suspeitos", 0)
        dia = getattr(self, "dia_mais_sus", "N/A")
        dia_value = (
            f"{dia} ({getattr(self, 'sus_dia_mais_sus', '0')})"
            if dia != "N/A"
            else "N/A"
        )

        return [
            {
                "title": "Número total de registros",
                "value": str(getattr(self, "total_deteccoes", 0)),
            },
            {
                "title": "Número de registros suspeitos",
                "value": str(num_suspeitos if num_suspeitos is not None else 0),
            },
            {
                "title": "Dia com mais registros suspeitos",
                "value": dia_value,
            },
        ]

    def _build_daily_sections(
        self, daily_figs: list[dict[str, str]], suspeitos: pd.DataFrame | None
    ) -> list[dict[str, Any]]:
        if not daily_figs:
            return []

        daily_tables = self.results.get("daily_tables", {}) or {}
        tracks_by_day = self.results.get("daily_track_tables", {}) or {}
        df_sus_all = (
            suspeitos if isinstance(suspeitos, pd.DataFrame) else pd.DataFrame()
        )

        def _parse_day(day: str) -> datetime:
            try:
                return datetime.strptime(day, "%d/%m/%Y")
            except Exception:
                return datetime.max

        sections: list[dict[str, Any]] = []
        for fig in sorted(
            daily_figs, key=lambda item: _parse_day(item.get("date", ""))
        ):
            day_key = fig.get("date")
            table = self._build_table_data(
                self._get_day_data(daily_tables, day_key, df_sus_all),
                ["Data", "Origem", "Destino", "Km", "s", "Km/h"],
            )
            tracks = self._build_track_sections(day_key, tracks_by_day)

            sections.append(
                {
                    "date": day_key,
                    "map_path": self._safe_path(fig.get("path")),
                    "table": table,
                    "has_table": bool(table["rows"]),
                    "tracks": tracks,
                    "has_tracks": any(track["table"]["rows"] for track in tracks),
                }
            )

        return sections

    def _build_track_sections(
        self, day_key: str | None, tracks_by_day: dict[str, Any]
    ) -> list[dict[str, Any]]:
        if not day_key or not isinstance(tracks_by_day, dict):
            return []

        tracks = tracks_by_day.get(day_key)
        if not isinstance(tracks, dict):
            return []

        df_c1, df_c2 = self._get_track_dataframes(tracks)
        has_tracks = self._check_tracks_exist(df_c1, df_c2)
        pngs = self._generate_trail_maps(day_key, tracks) if has_tracks else {}

        sections = []

        if isinstance(df_c1, pd.DataFrame) and not df_c1.empty:
            sections.append(
                {
                    "title": f"Trilha - Carro 1 - {day_key}",
                    "map_path": self._safe_path(pngs.get("carro1")),
                    "table": self._build_table_data(df_c1),
                }
            )

        if isinstance(df_c2, pd.DataFrame) and not df_c2.empty:
            sections.append(
                {
                    "title": f"Trilha - Carro 2 - {day_key}",
                    "map_path": self._safe_path(pngs.get("carro2")),
                    "table": self._build_table_data(df_c2),
                }
            )

        for section in sections:
            section["has_table"] = bool(section["table"]["rows"])

        return sections

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #
    def _build_table_data(
        self, df: pd.DataFrame | None, columns: list[str] | None = None
    ) -> dict[str, Any]:
        if not isinstance(df, pd.DataFrame) or df.empty:
            return {"headers": columns or [], "rows": []}

        if columns:
            available_cols = [col for col in columns if col in df.columns]
            df_sel = df[available_cols].copy()
        else:
            available_cols = list(df.columns)
            df_sel = df.copy()

        df_sel = df_sel.fillna("")

        rows = []
        for record in df_sel.to_dict(orient="records"):
            row = [
                self._format_cell_value(record.get(col, "")) for col in available_cols
            ]
            rows.append(row)

        return {"headers": available_cols, "rows": rows}

    @staticmethod
    def _format_cell_value(value: Any) -> str:
        if isinstance(value, float):
            if pd.isna(value):
                return ""
            if float(value).is_integer():
                return str(int(value))
            return f"{value:.2f}"
        if pd.isna(value):
            return ""
        return str(value)

    def _format_analysis_period(self) -> str:
        inicio = getattr(self, "periodo_inicio", None)
        fim = getattr(self, "periodo_fim", None)

        if inicio and fim:
            return f"De {inicio:%d/%m/%Y às %H:%M:%S} até {fim:%d/%m/%Y às %H:%M:%S}"

        return "Período não informado"
