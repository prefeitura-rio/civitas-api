# -*- coding: utf-8 -*-
"""
pair_detection.py — Suspicious pair detection logic
--------------------------------------------------
Single responsibility: Detect suspicious consecutive pairs
"""
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from ..utils import haversine_km


class PairDetector:
    """Detects suspicious consecutive detection pairs"""
    
    @classmethod
    def find_suspicious_pairs(cls, df: pd.DataFrame, speed_limit: float) -> pd.DataFrame:
        """Find all suspicious consecutive pairs above speed limit"""
        pairs_data = cls._scan_consecutive_pairs(df, speed_limit)
        return pd.DataFrame(pairs_data)
    
    @classmethod
    def _scan_consecutive_pairs(cls, df: pd.DataFrame, speed_limit: float) -> List[Dict[str, Any]]:
        """Scan all consecutive pairs for speed violations"""
        pairs = []
        
        for i in range(len(df) - 1):
            pair_data = cls._analyze_pair(df.iloc[i], df.iloc[i+1], speed_limit)
            if pair_data:
                pairs.append(pair_data)
                
        return pairs
    
    @classmethod
    def _analyze_pair(cls, detection_a: pd.Series, detection_b: pd.Series, speed_limit: float) -> Optional[Dict[str, Any]]:
        """Analyze a single pair of detections"""
        try:
            distance_km = cls._calculate_distance(detection_a, detection_b)
            time_diff_seconds = cls._calculate_time_difference(detection_a, detection_b)
            
            if time_diff_seconds <= 0:
                return None
                
            speed_kmh = cls._calculate_speed(distance_km, time_diff_seconds)
            
            if speed_kmh > speed_limit:
                return cls._create_pair_record(detection_a, detection_b, distance_km, time_diff_seconds, speed_kmh)
                
        except Exception:
            return None
    
    @staticmethod
    def _calculate_distance(detection_a: pd.Series, detection_b: pd.Series) -> float:
        """Calculate distance between two detections"""
        return haversine_km(
            float(detection_a['latitude']), float(detection_a['longitude']),
            float(detection_b['latitude']), float(detection_b['longitude'])
        )
    
    @staticmethod
    def _calculate_time_difference(detection_a: pd.Series, detection_b: pd.Series) -> float:
        """Calculate time difference in seconds"""
        return (pd.to_datetime(detection_b['datahora']) - pd.to_datetime(detection_a['datahora'])).total_seconds()
    
    @staticmethod
    def _calculate_speed(distance_km: float, time_seconds: float) -> float:
        """Calculate speed in km/h"""
        return distance_km / (time_seconds / 3600.0)
    
    @staticmethod
    def _create_pair_record(detection_a: pd.Series, detection_b: pd.Series, 
                           distance_km: float, time_seconds: float, speed_kmh: float) -> Dict[str, Any]:
        """Create pair record with all required fields"""
        base_record = PairDetector._create_timestamp_fields(detection_a, detection_b)
        base_record.update(PairDetector._create_location_fields(detection_a, detection_b))
        base_record.update(PairDetector._create_measurement_fields(distance_km, time_seconds, speed_kmh))
        base_record.update(PairDetector._create_coordinate_fields(detection_a, detection_b))
        base_record.update(PairDetector._create_metadata_fields(detection_a, detection_b))
        return base_record
    
    @staticmethod
    def _create_timestamp_fields(detection_a: pd.Series, detection_b: pd.Series) -> Dict[str, Any]:
        """Create timestamp-related fields"""
        dt_a = pd.to_datetime(detection_a['datahora'])
        dt_b = pd.to_datetime(detection_b['datahora'])
        return {
            'Data': dt_a,
            'DataDestino': dt_b,
            'Data_ts': dt_a,
            'DataFormatada': dt_a.strftime('%d/%m/%Y %H:%M:%S'),
        }
    
    @staticmethod
    def _create_location_fields(detection_a: pd.Series, detection_b: pd.Series) -> Dict[str, Any]:
        """Create location-related fields"""
        return {
            'Origem': detection_a['localidade (codcet)'],
            'Destino': detection_b['localidade (codcet)'],
        }
    
    @staticmethod
    def _create_measurement_fields(distance_km: float, time_seconds: float, speed_kmh: float) -> Dict[str, Any]:
        """Create measurement fields"""
        return {
            'Km': float(distance_km),
            's': float(time_seconds),
            'Km/h': float(speed_kmh),
        }
    
    @staticmethod
    def _create_coordinate_fields(detection_a: pd.Series, detection_b: pd.Series) -> Dict[str, Any]:
        """Create coordinate fields"""
        return {
            'latitude_1': float(detection_a['latitude']),
            'longitude_1': float(detection_a['longitude']),
            'latitude_2': float(detection_b['latitude']),
            'longitude_2': float(detection_b['longitude']),
            'Latitude': float(detection_a['latitude']),
            'Longitude': float(detection_a['longitude']),
        }
    
    @staticmethod
    def _create_metadata_fields(detection_a: pd.Series, detection_b: pd.Series) -> Dict[str, Any]:
        """Create metadata fields"""
        return {
            'bairro_origem': detection_a.get('bairro'),
            'bairro_destino': detection_b.get('bairro'),
            'localidade_origem': detection_a.get('localidade'),
            'localidade_destino': detection_b.get('localidade'),
            'velocidade_origem': detection_a.get('velocidade'),
            'velocidade_destino': detection_b.get('velocidade'),
        }