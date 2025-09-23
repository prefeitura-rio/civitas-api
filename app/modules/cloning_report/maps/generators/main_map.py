"""Main map generation - fully refactored OO implementation"""
import pandas as pd
from typing import Optional

from ...utils import VMAX_KMH
from .map_generator import MapGenerator


def generate_map_clonagem(
    df_pairs: pd.DataFrame,
    use_clusters: bool = True,
    vmax_kmh: float = VMAX_KMH,
    verbose: bool = False,
    *,
    base_only: bool = False,
    df_all: Optional[pd.DataFrame] = None,
    show_other_daily: bool = False,
    include_non_sus_days: bool = False,
) -> str:
    """Generate main cloning detection map - fully refactored OO implementation"""
    generator = MapGenerator(use_clusters, vmax_kmh, verbose)
    return generator.generate_map_clonagem(
        df_pairs, base_only=base_only, df_all=df_all, 
        show_other_daily=show_other_daily, include_non_sus_days=include_non_sus_days
    )
