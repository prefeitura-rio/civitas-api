"""Single day map generation"""

import pandas as pd
from app.modules.cloning_report.utils import VMAX_KMH


def generate_map_clonagem_single_day_html(
    df_pairs: pd.DataFrame, use_clusters: bool = True, vmax_kmh: float = VMAX_KMH
) -> str:
    """Generate map HTML for single day data"""
    # Import from local module to avoid circular dependency
    from app.modules.cloning_report.maps.generators.main_map import (
        generate_map_clonagem,
    )

    if df_pairs is None or df_pairs.empty:
        return generate_map_clonagem(
            df_pairs, use_clusters=use_clusters, vmax_kmh=vmax_kmh
        )

    df = df_pairs.copy()
    ts = pd.to_datetime(df.get("Data_ts", df.get("Data")), errors="coerce", utc=True)
    if ts.isna().all():
        return generate_map_clonagem(
            df_pairs, use_clusters=use_clusters, vmax_kmh=vmax_kmh
        )

    first_day = ts.dt.strftime("%d/%m/%Y").iloc[0]
    df["_day_str"] = ts.dt.strftime("%d/%m/%Y")
    return generate_map_clonagem(
        df[df["_day_str"] == first_day].copy(),
        use_clusters=use_clusters,
        vmax_kmh=vmax_kmh,
    )
