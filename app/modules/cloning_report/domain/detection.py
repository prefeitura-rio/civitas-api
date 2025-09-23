"""Domain entities for detection data"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Detection:
    """Single vehicle detection event"""
    datetime: datetime
    plate: str
    equipment_code: str
    latitude: float
    longitude: float
    speed: Optional[float] = None
    neighborhood: str = ""
    locality: str = ""
    street: str = ""
    
    @property
    def location_display(self) -> str:
        """Formatted location for display"""
        return f"{self.locality} ({self.equipment_code})" if self.locality else f"({self.equipment_code})"


@dataclass
class SuspiciousPair:
    """Pair of detections with suspicious travel speed"""
    origin: Detection
    destination: Detection
    travel_speed_kmh: float
    travel_time_minutes: float
    distance_km: float
    
    @property
    def is_suspicious(self) -> bool:
        """Check if pair exceeds speed threshold"""
        return self.travel_speed_kmh > 110.0