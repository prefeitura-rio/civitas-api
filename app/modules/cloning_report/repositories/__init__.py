"""Repository pattern for data access"""

from app.modules.cloning_report.repositories.detection_repository import (
    DetectionRepository,
    DetectionMapper,
)
from app.modules.cloning_report.repositories.csv_detection_repository import (
    CSVDetectionRepository,
)
from app.modules.cloning_report.repositories.bigquery_detection_repository import (
    BigQueryDetectionRepository,
)
from app.modules.cloning_report.repositories.async_bigquery_detection_repository import (
    AsyncBigQueryDetectionRepository,
    AsyncDetectionRepositoryFactory,
)
from app.modules.cloning_report.repositories.repository_factory import (
    DetectionRepositoryFactory,
)

__all__ = [
    "DetectionRepository",
    "DetectionMapper",
    "CSVDetectionRepository",
    "BigQueryDetectionRepository",
    "AsyncBigQueryDetectionRepository",
    "DetectionRepositoryFactory",
    "AsyncDetectionRepositoryFactory",
]
