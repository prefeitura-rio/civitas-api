"""Analytics module - KPI calculations and data analysis for cloning detection"""

from app.modules.cloning_report.analytics.facade import (
    compute_clonagem_kpis,
    compute_bairro_pair_stats,
    plot_bairro_pair_stats,
    compute_hourly_profile,
    plot_hourly_histogram,
)

__all__ = [
    "compute_clonagem_kpis",
    "compute_bairro_pair_stats",
    "plot_bairro_pair_stats",
    "compute_hourly_profile",
    "plot_hourly_histogram",
]
