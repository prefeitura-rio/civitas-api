"""Analytics facade - maintains backward compatibility during refactoring"""

from typing import Any
import pandas as pd

from app.modules.cloning_report.analytics.calculators.kpi_calculator import (
    KpiCalculator,
)
from app.modules.cloning_report.analytics.calculators.neighborhood_analyzer import (
    NeighborhoodAnalyzer,
)
from app.modules.cloning_report.analytics.calculators.time_analyzer import TimeAnalyzer
from app.modules.cloning_report.analytics.visualizers.neighborhood_visualizer import (
    NeighborhoodVisualizer,
)
from app.modules.cloning_report.analytics.visualizers.time_visualizer import (
    TimeVisualizer,
)


def compute_clonagem_kpis(results: dict[str, Any]) -> dict[str, Any]:
    """Compute main cloning detection KPIs - delegates to KpiCalculator"""
    return KpiCalculator.compute_clonagem_kpis(results)


def compute_bairro_pair_stats(results: dict[str, Any]) -> pd.DataFrame:
    """Groups pairs by neighborhood and returns counts - delegates to NeighborhoodAnalyzer"""
    return NeighborhoodAnalyzer.compute_bairro_pair_stats(results)


def plot_bairro_pair_stats(df: pd.DataFrame, top_n: int = 12) -> str | None:
    """Create bar chart of top neighborhood pairs - delegates to NeighborhoodVisualizer"""
    return NeighborhoodVisualizer.plot_bairro_pair_stats(df, top_n)


def compute_hourly_profile(results: dict[str, Any]) -> pd.DataFrame:
    """Count records by hour - delegates to TimeAnalyzer"""
    return TimeAnalyzer.compute_hourly_profile(results)


def plot_hourly_histogram(df: pd.DataFrame) -> str | None:
    """Create hourly bar chart - delegates to TimeVisualizer"""
    return TimeVisualizer.plot_hourly_histogram(df)
