"""
Clustering pipeline - Orchestrates the complete clustering workflow
"""

from __future__ import annotations

import pandas as pd
from typing import Any
from app.modules.cloning_report.utils import VMAX_KMH

from app.modules.cloning_report.clustering.clustering_validator import (
    ClusteringValidator,
)
from app.modules.cloning_report.clustering.track_generator import TrackGenerator


class ClusteringPipeline:
    """Orchestrates the complete vehicle clustering and track generation workflow"""

    @staticmethod
    def build_daily_tracks(
        df_sus: pd.DataFrame, vmax_kmh: float = VMAX_KMH
    ) -> dict[str, dict]:
        """Builds daily track tables following clustering criteria"""
        if ClusteringPipeline._is_empty_input(df_sus):
            return {}

        prepared_df = ClusteringPipeline._prepare_input_data(df_sus)
        daily_results = {}

        for day, day_data in prepared_df.groupby("_day", sort=True):
            daily_result = ClusteringPipeline._process_single_day(
                day, day_data, vmax_kmh
            )
            if daily_result:
                daily_results[day] = daily_result

        return daily_results

    @staticmethod
    def _is_empty_input(df_sus: pd.DataFrame) -> bool:
        """Checks if input is empty"""
        return df_sus is None or df_sus.empty

    @staticmethod
    def _prepare_input_data(df_sus: pd.DataFrame) -> pd.DataFrame:
        """Prepares input data with day grouping"""
        df = df_sus.copy()
        df["Data_ts"] = pd.to_datetime(df["Data_ts"], errors="coerce", utc=True)
        df["_day"] = df["Data_ts"].dt.strftime("%d/%m/%Y")
        return df

    @staticmethod
    def _process_single_day(
        day: str, day_data: pd.DataFrame, vmax_kmh: float
    ) -> dict[str, Any]:
        """Processes clustering for a single day"""
        can_cluster, metadata = ClusteringValidator.is_clusterizable(day_data, vmax_kmh)

        if not can_cluster or not metadata.get("labels"):
            return None

        tracks = TrackGenerator.generate_tracks(
            metadata["df_nodes"], metadata["labels"]
        )

        return {
            "method": metadata.get("method"),
            "carro1": tracks["carro1"],
            "carro2": tracks["carro2"],
        }
