"""Domain entities for cloning detection"""

from datetime import datetime
from pydantic import BaseModel


class Detection(BaseModel):
    """Vehicle detection at a radar point"""

    plate: str
    timestamp: datetime
    latitude: float
    longitude: float
    location: str


class SuspiciousPair(BaseModel):
    """Pair of detections indicating possible cloning"""

    origin: Detection
    destination: Detection
    distance_km: float
    time_seconds: float
    speed_kmh: float


class CloningReport(BaseModel):
    """Complete cloning analysis report"""

    plate: str
    period_start: datetime
    period_end: datetime
    suspicious_pairs: list[SuspiciousPair]
    total_detections: int
    report_path: str | None = None
