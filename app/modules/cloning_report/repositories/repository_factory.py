"""Factory for creating detection repositories"""

from .detection_repository import DetectionRepository
from .bigquery_detection_repository import BigQueryDetectionRepository


class DetectionRepositoryFactory:
    """Factory for creating appropriate detection repositories"""

    @staticmethod
    def create_repository(
        source_type: str = "bigquery", **kwargs
    ) -> DetectionRepository:
        """Create appropriate repository based on environment"""

        if source_type.lower() == "bigquery":
            return BigQueryDetectionRepository(**kwargs)
        else:
            raise ValueError(f"Unknown repository type: {source_type}")

    @staticmethod
    def create_bigquery_repository(
        project_id: str, credentials_path: str | None = None
    ) -> BigQueryDetectionRepository:
        """Create production BigQuery repository"""
        return BigQueryDetectionRepository(
            project_id=project_id, credentials_path=credentials_path
        )
