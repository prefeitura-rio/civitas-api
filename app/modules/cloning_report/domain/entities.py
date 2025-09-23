"""Domain entities for cloning detection"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Detection:
    """Vehicle detection at a radar point"""
    plate: str
    timestamp: datetime
    latitude: float
    longitude: float
    location: str


@dataclass
class SuspiciousPair:
    """Pair of detections indicating possible cloning"""
    origin: Detection
    destination: Detection
    distance_km: float
    time_seconds: float
    speed_kmh: float


@dataclass
class CloningReport:
    """Complete cloning analysis report"""
    plate: str
    period_start: datetime
    period_end: datetime
    suspicious_pairs: List[SuspiciousPair]
    total_detections: int
    report_path: Optional[str] = None