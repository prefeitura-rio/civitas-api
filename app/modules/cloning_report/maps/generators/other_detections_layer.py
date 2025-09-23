"""Other detections layer implementation"""
import folium
import pandas as pd
import numpy as np
import math
from typing import Set, Tuple, Dict, Iterable
from collections import defaultdict

from ..utils.formatting import format_timestamp, normalize_timestamp, get_optional_field


class OtherDetectionsLayer:
    """Layer de outras detecções"""
    
    def __init__(self, map_obj: folium.Map, name: str = "Outras detecções (cinza)", 
                 show: bool = False, round_dec: int = 5):
        self.map_obj = map_obj
        self.name = name
        self.show = show
        self.round_dec = round_dec
        self.feature_group = folium.FeatureGroup(name=name, show=show)
    
    def add_to_map(self, df_day_all: pd.DataFrame, 
                   endpoints: Set[Tuple[float, float, pd.Timestamp]]) -> folium.FeatureGroup:
        """Adiciona layer de outras detecções ao mapa"""
        if df_day_all is None or df_day_all.empty:
            self.feature_group.add_to(self.map_obj)
            return self.feature_group
        
        used_endpoints = self._prepare_endpoints(endpoints)
        occupied_xy = self._get_occupied_coordinates(endpoints)
        buckets = self._group_detections(df_day_all, used_endpoints)
        
        for (latr_r, lonr_r), rows in buckets.items():
            self._add_bucket_markers(rows, latr_r, lonr_r, occupied_xy)
        
        self.feature_group.add_to(self.map_obj)
        return self.feature_group
    
    def _prepare_endpoints(self, endpoints: Set[Tuple[float, float, pd.Timestamp]]) -> Set[Tuple[float, float, pd.Timestamp]]:
        """Prepara endpoints para exclusão"""
        return {
            (round(float(lat), self.round_dec), round(float(lon), self.round_dec), ts)
            for (lat, lon, ts) in endpoints if not pd.isna(ts)
        }
    
    def _get_occupied_coordinates(self, endpoints: Set[Tuple[float, float, pd.Timestamp]]) -> Set[Tuple[float, float]]:
        """Obtém coordenadas ocupadas"""
        return {
            (round(float(lat), self.round_dec), round(float(lon), self.round_dec))
            for (lat, lon, _ts) in endpoints
            if not pd.isna(lat) and not pd.isna(lon)
        }
    
    def _group_detections(self, df_day_all: pd.DataFrame, 
                         used_endpoints: Set[Tuple[float, float, pd.Timestamp]]) -> Dict[Tuple[float, float], list]:
        """Agrupa detecções por coordenadas"""
        buckets = defaultdict(list)
        dfa = df_day_all.dropna(subset=['latitude','longitude','datahora']).copy()
        
        for _, r0 in dfa.iterrows():
            try:
                lat = float(r0['latitude'])
                lon = float(r0['longitude'])
            except Exception:
                continue
            
            ts0 = normalize_timestamp(r0['datahora'])
            key3 = (round(lat, self.round_dec), round(lon, self.round_dec), ts0)
            if ts0 is not pd.NaT and key3 in used_endpoints:
                continue
            
            buckets[(round(lat, self.round_dec), round(lon, self.round_dec))].append(r0)
        
        return buckets
    
    def _add_bucket_markers(self, rows: list, latr_r: float, lonr_r: float, 
                           occupied_xy: Set[Tuple[float, float]]) -> None:
        """Adiciona marcadores para um bucket de detecções"""
        rows = sorted(rows, key=lambda rr: normalize_timestamp(rr['datahora']))
        
        label = get_optional_field(rows[0], 'localidade', 'Localidade', 'logradouro', 'Logradouro',
                                 default=f"{latr_r}, {lonr_r}")
        
        vels = self._extract_velocities(rows)
        horas_fmt = [format_timestamp(rr['datahora']) for rr in rows]
        horas_fmt = [h for h in horas_fmt if h]
        horas_fmt = list(dict.fromkeys(horas_fmt))
        
        horas_str = horas_fmt[0] if len(horas_fmt) == 1 else " / ".join(horas_fmt)
        tooltip_txt = self._create_tooltip(label, horas_fmt)
        popup_txt = self._create_popup_text(label, horas_str, vels)
        
        lat_final, lon_final = self._find_non_overlapping_position(rows, occupied_xy)
        occupied_xy.add((round(lat_final, self.round_dec), round(lon_final, self.round_dec)))
        
        folium.Marker([lat_final, lon_final], icon=folium.Icon(icon="car", prefix="fa", color="gray"),
                     tooltip=tooltip_txt, popup=folium.Popup(popup_txt, max_width=360)).add_to(self.feature_group)
    
    def _extract_velocities(self, rows: list) -> list:
        """Extrai velocidades das detecções"""
        vels = []
        for rr in rows:
            vv = pd.to_numeric(get_optional_field(rr, 'velocidade', 'Velocidade'), errors='coerce')
            if pd.notna(vv) and float(vv) >= 0:
                vels.append(float(vv))
        return vels
    
    def _create_tooltip(self, label: str, horas_fmt: list) -> str:
        """Cria tooltip para marcador"""
        if len(horas_fmt) <= 1:
            return f"{label} - {horas_fmt[0]}"
        return f"{label} - {horas_fmt[0]} – {horas_fmt[-1]} ({len(horas_fmt)} detecções)"
    
    def _create_popup_text(self, label: str, horas_str: str, vels: list) -> str:
        """Cria texto do popup"""
        lines = [
            f"<b>Localidade:</b> {label}",
            f"<b>Data/hora:</b> {horas_str}",
        ]
        
        if vels:
            if len(vels) == 1:
                vel_str = f"<b>Velocidade (radar):</b> {vels[0]:.0f} km/h"
            else:
                vel_str = f"<b>Velocidade (radar):</b> {min(vels):.0f}–{max(vels):.0f} km/h ({len(vels)} leituras)"
            lines.append(vel_str)
        
        return "<br>".join(lines)
    
    def _find_non_overlapping_position(self, rows: list, occupied_xy: Set[Tuple[float, float]]) -> Tuple[float, float]:
        """Encontra posição não sobreposta para marcador"""
        lats = [float(r['latitude']) for r in rows]
        lons = [float(r['longitude']) for r in rows]
        lat0 = float(np.mean(lats))
        lon0 = float(np.mean(lons))
        
        base_key = (round(lat0, self.round_dec), round(lon0, self.round_dec))
        if base_key not in occupied_xy:
            return lat0, lon0
        
        radii_m = [6, 10, 14, 18, 22, 26, 30]
        angles_deg = [0, 60, 120, 180, 240, 300]
        
        for r in radii_m:
            for ang in angles_deg:
                dlat_m = r * math.sin(math.radians(ang))
                dlon_m = r * math.cos(math.radians(ang))
                dlat_deg, dlon_deg = self._meters_to_deg(lat0, dlat_m, dlon_m)
                lat2 = lat0 + dlat_deg
                lon2 = lon0 + dlon_deg
                key2 = (round(lat2, self.round_dec), round(lon2, self.round_dec))
                if key2 not in occupied_xy:
                    return lat2, lon2
        
        return lat0, lon0
    
    def _meters_to_deg(self, lat_deg: float, dlat_m: float, dlon_m: float) -> Tuple[float, float]:
        """Converte metros para graus"""
        deg_lat = dlat_m / 111_320.0
        cos_lat = math.cos(math.radians(lat_deg if not math.isnan(lat_deg) else 0.0))
        cos_lat = max(cos_lat, 1e-6)
        deg_lon = dlon_m / (111_320.0 * cos_lat)
        return deg_lat, deg_lon
