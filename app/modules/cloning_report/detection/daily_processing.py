"""
daily_processing.py - Daily data processing
"""

from typing import Any
import pandas as pd


class DailyProcessor:
    """Processes daily detection data and creates tables"""

    @staticmethod
    def create_daily_figures(suspicious_pairs: pd.DataFrame) -> list[dict[str, str]]:
        """Create daily figures with error handling"""
        try:
            return DailyProcessor._generate_daily_figures(suspicious_pairs)
        except Exception as e:
            print(e)
            print(suspicious_pairs)
            return []

    @staticmethod
    def _generate_daily_figures(suspicious_pairs: pd.DataFrame) -> list[dict[str, str]]:
        """Generate daily figures using maps module"""
        # Import here to avoid circular dependency
        import sys

        sys.path.append(".")
        from app.modules.cloning_report.maps import render_daily_figures

        return render_daily_figures(suspicious_pairs)

    @staticmethod
    def create_daily_tables(
        suspicious_pairs: pd.DataFrame,
    ) -> dict[str, dict[str, pd.DataFrame]]:
        """Create daily tables from suspicious pairs"""
        if suspicious_pairs.empty:
            return {}

        prepared_data = DailyProcessor._prepare_daily_data(suspicious_pairs)
        return DailyProcessor._group_by_day(prepared_data)

    @staticmethod
    def _prepare_daily_data(df: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for daily grouping"""
        tmp = df.copy()
        tmp["Data_ts"] = pd.to_datetime(tmp["Data_ts"], errors="coerce")
        tmp["_day"] = tmp["Data_ts"].dt.strftime("%d/%m/%Y")
        return tmp

    @staticmethod
    def _group_by_day(df: pd.DataFrame) -> dict[str, dict[str, pd.DataFrame]]:
        """Group data by day and create tables"""
        daily_tables = {}
        required_cols = [
            "Data",
            "DataDestino",
            "DataFormatada",
            "Origem",
            "Destino",
            "Km",
            "s",
            "Km/h",
            "latitude_1",
            "longitude_1",
            "latitude_2",
            "longitude_2",
        ]

        for day, group in df.groupby("_day", sort=True):
            table_data = DailyProcessor._extract_table_columns(group, required_cols)
            daily_tables[day] = {"todas": table_data.reset_index(drop=True)}

        return daily_tables

    @staticmethod
    def _extract_table_columns(
        group: pd.DataFrame, required_cols: list[str]
    ) -> pd.DataFrame:
        """Extract required columns from group"""
        available_cols = set(required_cols).intersection(group.columns)
        return group[list(available_cols)].copy() if available_cols else group.copy()

    @staticmethod
    def create_track_tables(suspicious_pairs: pd.DataFrame, speed_limit: float) -> Any:
        """Create daily track tables"""
        # Import here to avoid circular dependency
        import sys

        sys.path.append(".")
        from app.modules.cloning_report.clustering.clustering_pipeline import (
            ClusteringPipeline,
        )

        return ClusteringPipeline.build_daily_tracks(
            suspicious_pairs, vmax_kmh=speed_limit
        )
