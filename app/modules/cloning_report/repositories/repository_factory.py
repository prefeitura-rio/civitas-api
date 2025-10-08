"""Factory for creating detection repositories"""

import os

from .detection_repository import DetectionRepository
from .csv_detection_repository import CSVDetectionRepository
from .bigquery_detection_repository import BigQueryDetectionRepository


class DetectionRepositoryFactory:
    """Factory for creating appropriate detection repositories"""

    @staticmethod
    def create_repository(source_type: str = "csv", **kwargs) -> DetectionRepository:
        """Create appropriate repository based on environment"""

        if source_type == "csv":
            if os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv(
                "GOOGLE_APPLICATION_CREDENTIALS"
            ):
                source_type = "bigquery"
            else:
                source_type = "csv"

        if source_type.lower() == "bigquery":
            return BigQueryDetectionRepository(**kwargs)
        elif source_type.lower() == "csv":
            return CSVDetectionRepository(**kwargs)
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

    @staticmethod
    def create_csv_repository(
        data_directory: str = "dados_placas",
    ) -> CSVDetectionRepository:
        """Create development CSV repository"""
        return CSVDetectionRepository(data_directory=data_directory)
