"""Data processing utilities for map generation"""
import pandas as pd
from typing import Optional, Tuple


class DataProcessor:
    """Processa dados para o mapa"""
    
    def __init__(self, df_pairs: pd.DataFrame):
        self.df_pairs = df_pairs.copy()
        self._process_timestamps()
        self._add_day_strings()
    
    def _process_timestamps(self) -> None:
        """Processa timestamps dos dados"""
        ts = pd.to_datetime(
            self.df_pairs.get("Data_ts", self.df_pairs.get("Data")), 
            errors="coerce", 
            utc=True
        )
        self.df_pairs["_processed_ts"] = ts
    
    def _add_day_strings(self) -> None:
        """Adiciona strings de dia formatadas"""
        self.df_pairs["_day_str"] = self.df_pairs["_processed_ts"].dt.strftime("%d/%m/%Y")
        self.df_pairs = self.df_pairs[self.df_pairs["_day_str"].notna()].copy()
    
    def get_ordered_days(self) -> list:
        """Retorna dias ordenados cronologicamente"""
        order = (
            self.df_pairs.assign(__k=pd.to_datetime(self.df_pairs["_day_str"], format="%d/%m/%Y", errors="coerce"))
              .groupby("_day_str")["__k"].min().sort_values(kind="stable").index.tolist()
        )
        return order
    
    def get_day_data(self, day: str) -> pd.DataFrame:
        """Retorna dados de um dia específico"""
        return self.df_pairs[self.df_pairs["_day_str"] == day].reset_index(drop=True)
    
    def get_coordinates(self) -> Tuple[pd.Series, pd.Series]:
        """Retorna coordenadas válidas"""
        all_lats = pd.concat([self.df_pairs["latitude_1"], self.df_pairs["latitude_2"]], ignore_index=True).astype(float)
        all_lons = pd.concat([self.df_pairs["longitude_1"], self.df_pairs["longitude_2"]], ignore_index=True).astype(float)
        mask = all_lats.notna() & all_lons.notna()
        return all_lats[mask], all_lons[mask]
    
    def get_bounds_coordinates(self, df_all: Optional[pd.DataFrame] = None, 
                             show_other_daily: bool = False, 
                             include_non_sus_days: bool = False) -> Tuple[pd.Series, pd.Series]:
        """Retorna coordenadas para bounds do mapa"""
        pairs_lats = pd.to_numeric(pd.concat([self.df_pairs["latitude_1"], self.df_pairs["latitude_2"]], ignore_index=True), errors="coerce").dropna()
        pairs_lons = pd.to_numeric(pd.concat([self.df_pairs["longitude_1"], self.df_pairs["longitude_2"]], ignore_index=True), errors="coerce").dropna()
        
        extra_lats = pd.Series([], dtype=float)
        extra_lons = pd.Series([], dtype=float)
        if isinstance(df_all, pd.DataFrame) and (show_other_daily or include_non_sus_days):
            extra_lats = pd.to_numeric(df_all.get("latitude"), errors="coerce").dropna()
            extra_lons = pd.to_numeric(df_all.get("longitude"), errors="coerce").dropna()
        
        return pd.concat([pairs_lats, extra_lats], ignore_index=True), pd.concat([pairs_lons, extra_lons], ignore_index=True)
    
    def get_center(self) -> list:
        """Retorna centro do mapa"""
        pairs_lats = pd.to_numeric(pd.concat([self.df_pairs["latitude_1"], self.df_pairs["latitude_2"]], ignore_index=True), errors="coerce").dropna()
        pairs_lons = pd.to_numeric(pd.concat([self.df_pairs["longitude_1"], self.df_pairs["longitude_2"]], ignore_index=True), errors="coerce").dropna()
        
        return [float(pairs_lats.median()) if not pairs_lats.empty else -22.90,
                float(pairs_lons.median()) if not pairs_lons.empty else -43.20]
