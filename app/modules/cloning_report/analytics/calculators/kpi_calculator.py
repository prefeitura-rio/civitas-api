"""Main KPI calculation functionality"""
import pandas as pd
import numpy as np
from typing import Dict, Any


class KpiCalculator:
    """Calculates key performance indicators for cloning detection"""
    
    @staticmethod
    def compute_clonagem_kpis(results: Dict[str, Any]) -> Dict[str, Any]:
        """Compute main cloning detection KPIs"""
        sus_df = results.get('dataframe', pd.DataFrame())
        
        if not isinstance(sus_df, pd.DataFrame) or sus_df.empty:
            return KpiCalculator._get_empty_kpis()
        
        return KpiCalculator._calculate_all_kpis(sus_df)
    
    @staticmethod
    def _get_empty_kpis() -> Dict[str, Any]:
        """Return empty KPIs structure"""
        return {
            'num_suspeitos': 0, 'max_vel': 0,
            'dia_mais_sus': 'N/A', 'sus_dia_mais_sus': 0,
            'turno_mais_sus': 'N/A', 'turno_mais_sus_count': 0,
            'place_lider': 'N/A', 'place_lider_count': 0,
            'top_pair_str': 'N/A', 'top_pair_count': 0,
        }
    
    @staticmethod
    def _calculate_all_kpis(sus_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all KPIs from suspicious pairs dataframe"""
        kpis = {}
        kpis.update(KpiCalculator._get_basic_metrics(sus_df))
        kpis.update(KpiCalculator._get_temporal_analysis(sus_df))
        kpis.update(KpiCalculator._get_location_analysis(sus_df))
        return kpis
    
    @staticmethod
    def _get_basic_metrics(sus_df: pd.DataFrame) -> Dict[str, Any]:
        """Get basic count and speed metrics"""
        vel = pd.to_numeric(sus_df.get('Km/h', pd.Series([], dtype=float)), errors='coerce')
        return {
            'num_suspeitos': int(len(sus_df)),
            'max_vel': int(np.nanmax(vel)) if len(vel) else 0
        }
    
    @staticmethod
    def _get_temporal_analysis(sus_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze temporal patterns"""
        day_analysis = KpiCalculator._analyze_daily_patterns(sus_df)
        hour_analysis = KpiCalculator._analyze_hourly_patterns(sus_df)
        return {**day_analysis, **hour_analysis}
    
    @staticmethod
    def _analyze_daily_patterns(sus_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze which day has most suspicious activity"""
        day = pd.to_datetime(sus_df.get('Data_ts', sus_df.get('Data')), errors='coerce', utc=True).dt.strftime('%d/%m/%Y')
        
        if day.notna().any():
            counts = day.value_counts()
            return {
                'dia_mais_sus': str(counts.idxmax()),
                'sus_dia_mais_sus': int(counts.max())
            }
        else:
            return {'dia_mais_sus': 'N/A', 'sus_dia_mais_sus': 0}
    
    @staticmethod
    def _analyze_hourly_patterns(sus_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze which time period has most suspicious activity"""
        hour = pd.to_datetime(sus_df.get('Data_ts', sus_df.get('Data')), errors='coerce', utc=True).dt.tz_convert(None).dt.hour
        
        def _get_time_period(h):
            return 'Madrugada' if h < 6 else ('Manhã' if h < 12 else ('Tarde' if h < 18 else 'Noite'))
        
        period_counts = hour.dropna().astype(int).map(_get_time_period).value_counts()
        
        if not period_counts.empty:
            return {
                'turno_mais_sus': str(period_counts.idxmax()),
                'turno_mais_sus_count': int(period_counts.max())
            }
        else:
            return {'turno_mais_sus': 'N/A', 'turno_mais_sus_count': 0}
    
    @staticmethod
    def _get_location_analysis(sus_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze location patterns"""
        radar_analysis = KpiCalculator._analyze_radar_patterns(sus_df)
        pair_analysis = KpiCalculator._analyze_pair_patterns(sus_df)
        return {**radar_analysis, **pair_analysis}
    
    @staticmethod
    def _analyze_radar_patterns(sus_df: pd.DataFrame) -> Dict[str, Any]:
        """Find radar with most suspicious detections"""
        place = sus_df.get('Origem', pd.Series([], dtype=str)).astype(str)
        
        if not place.empty:
            counts = place.value_counts()
            return {
                'place_lider': str(counts.idxmax()),
                'place_lider_count': int(counts.max())
            }
        else:
            return {'place_lider': 'N/A', 'place_lider_count': 0}
    
    @staticmethod
    def _analyze_pair_patterns(sus_df: pd.DataFrame) -> Dict[str, Any]:
        """Find most common origin-destination pair"""
        if {'Origem', 'Destino'}.issubset(sus_df.columns):
            pairs = (sus_df['Origem'].astype(str) + ' → ' + sus_df['Destino'].astype(str))
            pair_counts = pairs.value_counts()
            
            if not pair_counts.empty:
                return {
                    'top_pair_str': str(pair_counts.idxmax()),
                    'top_pair_count': int(pair_counts.max())
                }
        
        return {'top_pair_str': 'N/A', 'top_pair_count': 0}