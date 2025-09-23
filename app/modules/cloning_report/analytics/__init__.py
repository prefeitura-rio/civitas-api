"""Analytics module - KPI calculations and data analysis for cloning detection"""

# Backward compatibility - import from facade
from .facade import (
    compute_clonagem_kpis,
    compute_bairro_pair_stats, 
    plot_bairro_pair_stats,
    compute_hourly_profile,
    plot_hourly_histogram
)

# New modular components (optional direct access)
from .calculators.kpi_calculator import KpiCalculator
from .calculators.neighborhood_analyzer import NeighborhoodAnalyzer
from .calculators.time_analyzer import TimeAnalyzer
from .visualizers.neighborhood_visualizer import NeighborhoodVisualizer
from .visualizers.time_visualizer import TimeVisualizer