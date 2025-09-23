"""Map-specific utilities for bounds and labels"""
import folium
import pandas as pd
from typing import Tuple
from folium.features import DivIcon


def fit_bounds_to_data(map_obj: folium.Map, lats: pd.Series, lons: pd.Series,
                      pad_ratio: float = 0.15, min_pad: float = 0.01) -> None:
    """Apply fit_bounds to map if there are valid coordinates (equivalent to _fit_bounds_map)"""
    if lats is None or lons is None or lats.empty or lons.empty:
        return
    lat_min, lat_max = float(lats.min()), float(lats.max())
    lon_min, lon_max = float(lons.min()), float(lons.max())
    dx, dy = max(lon_max - lon_min, 0.0), max(lat_max - lat_min, 0.0)
    pad_x = pad_ratio * dx if dx > 0 else min_pad
    pad_y = pad_ratio * dy if dy > 0 else min_pad
    bounds = [[lat_min - pad_y, lon_min - pad_x], [lat_max + pad_y, lon_max + pad_x]]
    try:
        map_obj.fit_bounds(bounds)
    except Exception:
        pass


def add_speed_label(point1: Tuple[float, float], point2: Tuple[float, float], 
                   speed_kmh: float, layer) -> None:
    """Add speed label at midpoint between two coordinates (equivalent to _speed_label)"""
    lat_mid = (float(point1[0]) + float(point2[0])) / 2.0
    lon_mid = (float(point1[1]) + float(point2[1])) / 2.0
    folium.Marker(
        [lat_mid, lon_mid],
        icon=DivIcon(
            icon_size=(100, 24), icon_anchor=(50, 12),
            html=(
                '<div style="font-size:10pt;font-weight:700;color:#9b1111;'
                'background:rgba(255,255,255,0.95);padding:4px 6px;border-radius:6px;'
                'border:1px solid #caa;box-shadow:0 0 4px rgba(0,0,0,.15);">'
                f'{int(round(float(speed_kmh)))} km/h</div>'
            )
        ),
    ).add_to(layer)