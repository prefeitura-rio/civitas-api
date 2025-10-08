"""Time-based analysis functionality"""

import pandas as pd
from typing import Any


class TimeAnalyzer:
    """Analyzes temporal patterns in cloning detection data"""

    @staticmethod
    def compute_hourly_profile(results: dict[str, Any]) -> pd.DataFrame:
        """Count suspicious records by hour (0-23)"""
        sus_df = results.get("dataframe", pd.DataFrame())

        if not isinstance(sus_df, pd.DataFrame) or sus_df.empty:
            return TimeAnalyzer._get_empty_profile()

        return TimeAnalyzer._analyze_hourly_patterns(sus_df)

    @staticmethod
    def _get_empty_profile() -> pd.DataFrame:
        """Return empty hourly profile structure"""
        return pd.DataFrame({"Hora": [], "Contagem": []})

    @staticmethod
    def _analyze_hourly_patterns(sus_df: pd.DataFrame) -> pd.DataFrame:
        """Extract and analyze hourly patterns from data"""
        hour_series = TimeAnalyzer._extract_hour_series(sus_df)
        counts = TimeAnalyzer._count_by_hour(hour_series)
        return TimeAnalyzer._format_hourly_results(counts)

    @staticmethod
    def _extract_hour_series(sus_df: pd.DataFrame) -> pd.Series:
        """Extract hour from datetime columns"""
        datetime_col = sus_df.get("Data_ts", sus_df.get("Data"))
        return (
            pd.to_datetime(datetime_col, errors="coerce", utc=True)
            .dt.tz_convert(None)
            .dt.hour
        )

    @staticmethod
    def _count_by_hour(hour_series: pd.Series) -> pd.Series:
        """Count occurrences by hour and sort by hour"""
        return hour_series.dropna().astype(int).value_counts().sort_index()

    @staticmethod
    def _format_hourly_results(counts: pd.Series) -> pd.DataFrame:
        """Format hour counts into DataFrame"""
        return pd.DataFrame({"Hora": counts.index, "Contagem": counts.values})
