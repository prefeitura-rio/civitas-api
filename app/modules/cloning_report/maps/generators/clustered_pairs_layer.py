"""Clustered pairs layer implementation"""
import folium
import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, Set

from ...utils import BLUE_LIGHT, BLUE_DARK, haversine_km
from ..utils.formatting import format_timestamp, normalize_timestamp, get_optional_field
from ..utils.mapping import add_speed_label


class ClusteredPairsLayer:
    """Layer de pares clusterizados"""
    
    def __init__(self, map_obj: folium.Map, name: str, show: bool = False):
        self.map_obj = map_obj
        self.name = name
        self.show = show
        self.feature_group = folium.FeatureGroup(name=name, show=show)
        self.endpoints: Set[Tuple[float, float, pd.Timestamp]] = set()
    
    def add_to_map(self, df_pairs_day: pd.DataFrame, labels: Optional[Dict[str, int]] = None) -> Tuple[folium.FeatureGroup, Set[Tuple[float, float, pd.Timestamp]]]:
        """Adiciona layer de pares clusterizados ao mapa"""
        if df_pairs_day is None or df_pairs_day.empty:
            self.feature_group.add_to(self.map_obj)
            return self.feature_group, self.endpoints
        
        labels = labels or {}
        for j, r in df_pairs_day.iterrows():
            self._add_pair_to_layer(r, j, labels)
        
        self.feature_group.add_to(self.map_obj)
        return self.feature_group, self.endpoints
    
    def _add_pair_to_layer(self, row: pd.Series, index: int, labels: Dict[str, int]) -> None:
        """Adiciona um par ao layer"""
        coords = self._extract_coordinates(row)
        if not coords:
            return
        
        p1, p2 = coords
        times = self._extract_times(row)
        t1, t2 = times
        locations = self._extract_locations(row)
        local_origem, local_destino = locations
        velocity = self._calculate_velocity(row, p1, p2, t1, t2)
        colors = self._get_colors(row, t1, t2, labels, index)
        col1, col2 = colors
        
        self._add_edge_if_valid(p1, p2, velocity, labels)
        self._add_markers(p1, p2, t1, t2, local_origem, local_destino, velocity, col1, col2)
    
    def _extract_coordinates(self, row: pd.Series) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Extrai coordenadas do par"""
        try:
            p1 = (float(row['latitude_1']), float(row['longitude_1']))
            p2 = (float(row['latitude_2']), float(row['longitude_2']))
            return p1, p2
        except Exception:
            return None
    
    def _extract_times(self, row: pd.Series) -> Tuple[pd.Timestamp, pd.Timestamp]:
        """Extrai timestamps do par"""
        t1 = pd.to_datetime(row.get('Data_ts', row.get('Data')), errors='coerce', utc=True)
        t2 = pd.to_datetime(row.get('DataDestino', t1), errors='coerce', utc=True)
        return t1, t2
    
    def _extract_locations(self, row: pd.Series) -> Tuple[str, str]:
        """Extrai localidades do par"""
        local_origem = get_optional_field(
            row, 'localidade_origem', 'Localidade_Origem', 'localidade', 'Localidade',
            default=str(row.get('Origem','') or '').strip()
        )
        local_destino = get_optional_field(
            row, 'localidade_destino', 'Localidade_Destino', 'localidade', 'Localidade',
            default=str(row.get('Destino','') or '').strip()
        )
        return local_origem, local_destino
    
    def _calculate_velocity(self, row: pd.Series, p1: Tuple[float, float], 
                          p2: Tuple[float, float], t1: pd.Timestamp, t2: pd.Timestamp) -> float:
        """Calcula velocidade implícita"""
        v_measured = pd.to_numeric(row.get('Km/h'), errors='coerce')
        if pd.notna(v_measured):
            return float(v_measured)
        
        dist_km = haversine_km(p1[0], p1[1], p2[0], p2[1])
        dt_h = (t2 - t1).total_seconds() / 3600.0 if (pd.notna(t1) and pd.notna(t2)) else np.nan
        return (dist_km / dt_h) if (dt_h and dt_h > 0) else np.nan
    
    def _get_colors(self, row: pd.Series, t1: pd.Timestamp, t2: pd.Timestamp, 
                   labels: Dict[str, int], index: int) -> Tuple[str, Optional[str]]:
        """Determina cores baseadas em clusterização"""
        if not labels:
            return "gray", "gray"
        
        p1 = (float(row['latitude_1']), float(row['longitude_1']))
        p2 = (float(row['latitude_2']), float(row['longitude_2']))
        same_point = (round(p1[0],6) == round(p2[0],6)) and (round(p1[1],6) == round(p2[1],6))
        same_second = (pd.notna(t1) and pd.notna(t2) and t1.floor('s') == t2.floor('s'))
        
        nid1 = f"{t1.isoformat()}|{round(p1[0],6)}|{round(p1[1],6)}|{index}a"
        c1 = int(labels.get(nid1, 0))
        col1 = BLUE_LIGHT if c1 == 0 else BLUE_DARK
        
        c2 = None
        col2 = None
        if not (same_point and same_second):
            nid2 = f"{t2.isoformat()}|{round(p2[0],6)}|{round(p2[1],6)}|{index}b"
            c2 = int(labels.get(nid2, 1))
            col2 = BLUE_LIGHT if c2 == 0 else BLUE_DARK
        
        return col1, col2
    
    def _add_edge_if_valid(self, p1: Tuple[float, float], p2: Tuple[float, float], 
                          velocity: float, labels: Dict[str, int]) -> None:
        """Adiciona aresta se válida"""
        same_point = (round(p1[0],6) == round(p2[0],6)) and (round(p1[1],6) == round(p2[1],6))
        if not same_point:
            color = "#D30707" if labels else "#808080"
            folium.PolyLine([p1, p2], color=color, weight=3.5, opacity=0.95, dash_array="5, 10").add_to(self.feature_group)
            if pd.notna(velocity):
                add_speed_label(p1, p2, float(velocity), self.feature_group)
    
    def _add_markers(self, p1: Tuple[float, float], p2: Tuple[float, float], 
                    t1: pd.Timestamp, t2: pd.Timestamp, local_origem: str, 
                    local_destino: str, velocity: float, col1: str, col2: Optional[str]) -> None:
        """Adiciona marcadores ao layer"""
        same_point = (round(p1[0],6) == round(p2[0],6)) and (round(p1[1],6) == round(p2[1],6))
        same_second = (pd.notna(t1) and pd.notna(t2) and t1.floor('s') == t2.floor('s'))
        
        vel_str = f"{velocity:.1f} km/h" if pd.notna(velocity) else "n/d"
        
        popup_origem = self._create_popup(local_origem, local_destino, t1, vel_str, "seguinte")
        popup_destino = self._create_popup(local_destino, local_origem, t2, vel_str, "anterior")
        
        folium.Marker([p1[0], p1[1]], icon=folium.Icon(icon="car", prefix="fa", color=col1),
                     tooltip=format_timestamp(t1), popup=popup_origem).add_to(self.feature_group)
        self.endpoints.add((p1[0], p1[1], normalize_timestamp(t1)))
        
        if col2 is not None:
            folium.Marker([p2[0], p2[1]], icon=folium.Icon(icon="car", prefix="fa", color=col2),
                         tooltip=format_timestamp(t2), popup=popup_destino).add_to(self.feature_group)
            self.endpoints.add((p2[0], p2[1], normalize_timestamp(t2)))
    
    def _create_popup(self, local: str, other_local: str, timestamp: pd.Timestamp, 
                     velocity_str: str, relation: str) -> folium.Popup:
        """Cria popup para marcador"""
        return folium.Popup(
            "<br>".join([
                f"<b>Localidade:</b> {local}",
                f"<b>Detecção {relation}:</b> {other_local if other_local else '—'}",
                f"<b>Data/hora:</b> {format_timestamp(timestamp)}",
                f"<b>Velocidade (implícita):</b> {velocity_str}",
            ]), max_width=360
        )
