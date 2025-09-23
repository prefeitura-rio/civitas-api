# -*- coding: utf-8 -*-
"""
geography.py - Geographic calculations
-------------------------------------
Single responsibility: Handle geographic distance calculations
"""
import math


class GeographyService:
    """Handle geographic calculations following SRP"""
    
    EARTH_RADIUS_KM = 6371.0088
    
    @classmethod
    def haversine_distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate Haversine distance between two points in kilometers"""
        coordinates = cls._convert_to_radians(lat1, lon1, lat2, lon2)
        deltas = cls._calculate_deltas(*coordinates)
        
        return cls._haversine_formula(*coordinates, *deltas)
    
    @staticmethod
    def _convert_to_radians(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple:
        """Convert coordinates to radians"""
        return tuple(map(math.radians, (float(lat1), float(lon1), float(lat2), float(lon2))))
    
    @staticmethod
    def _calculate_deltas(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple:
        """Calculate latitude and longitude deltas"""
        return lat2 - lat1, lon2 - lon1
    
    @classmethod
    def _haversine_formula(cls, lat1: float, lon1: float, lat2: float, lon2: float, dlat: float, dlon: float) -> float:
        """Apply Haversine formula"""
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*(math.sin(dlon/2)**2)
        return 2 * cls.EARTH_RADIUS_KM * math.asin(math.sqrt(a))