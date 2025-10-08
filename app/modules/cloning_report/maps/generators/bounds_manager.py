"""Bounds management for map generation"""

import folium
import pandas as pd


class BoundsManager:
    """Gerencia bounds do mapa"""

    @staticmethod
    def fit_simple_bounds(m: folium.Map, lats: pd.Series, lons: pd.Series) -> None:
        """Aplica bounds simples ao mapa"""
        lat_min, lat_max = float(lats.min()), float(lats.max())
        lon_min, lon_max = float(lons.min()), float(lons.max())
        dx, dy = max(lon_max - lon_min, 0.0), max(lat_max - lat_min, 0.0)
        pad_x = 0.15 * dx if dx > 0 else 0.01
        pad_y = 0.15 * dy if dy > 0 else 0.01
        bounds = [
            [lat_min - pad_y, lon_min - pad_x],
            [lat_max + pad_y, lon_max + pad_x],
        ]
        try:
            m.fit_bounds(bounds)
        except Exception:
            pass
