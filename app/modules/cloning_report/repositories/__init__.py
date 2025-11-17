"""Repository pattern for data access"""

from app.modules.cloning_report.repositories.detection_repository import (
    DetectionRepository,
    DetectionMapper,
)
from app.modules.cloning_report.repositories.bigquery_detection_repository import (
    BigQueryDetectionRepository,
)
from app.modules.cloning_report.repositories.async_bigquery_detection_repository import (
    AsyncBigQueryDetectionRepository,
    AsyncDetectionRepositoryFactory,
)

__all__ = [
    "DetectionRepository",
    "DetectionMapper",
    "BigQueryDetectionRepository",
    "AsyncBigQueryDetectionRepository",
    "AsyncDetectionRepositoryFactory",
]
