"""Neighborhood pair analysis functionality"""

import pandas as pd
from typing import Any


class NeighborhoodAnalyzer:
    """Analyzes patterns in neighborhood pairs for cloning detection"""

    @staticmethod
    def compute_bairro_pair_stats(results: dict[str, Any]) -> pd.DataFrame:
        """Groups pairs by neighborhood and returns counts"""
        sus_df = results.get("dataframe", pd.DataFrame())

        if not isinstance(sus_df, pd.DataFrame) or sus_df.empty:
            return NeighborhoodAnalyzer._get_empty_dataframe()

        return NeighborhoodAnalyzer._analyze_neighborhood_pairs(sus_df)

    @staticmethod
    def _get_empty_dataframe() -> pd.DataFrame:
        """Return empty DataFrame with correct structure"""
        return pd.DataFrame(columns=["Bairro Origem", "Bairro Destino", "Contagem"])

    @staticmethod
    def _analyze_neighborhood_pairs(sus_df: pd.DataFrame) -> pd.DataFrame:
        """Analyze neighborhood pair patterns"""
        columns = ["bairro_origem", "bairro_destino"]

        if not set(columns).issubset(sus_df.columns):
            return NeighborhoodAnalyzer._get_empty_dataframe()

        return NeighborhoodAnalyzer._group_and_sort_pairs(sus_df, columns)

    @staticmethod
    def _group_and_sort_pairs(sus_df: pd.DataFrame, columns: list) -> pd.DataFrame:
        """Group by neighborhood pairs and sort by count"""
        grouped = (
            sus_df.groupby(columns, dropna=False).size().reset_index(name="Contagem")
        )
        renamed = grouped.rename(
            columns={
                "bairro_origem": "Bairro Origem",
                "bairro_destino": "Bairro Destino",
            }
        )
        return renamed.sort_values(
            "Contagem", ascending=False, kind="stable"
        ).reset_index(drop=True)
