"""BigQuery implementation of detection repository"""

from datetime import datetime
import os

from google.cloud import bigquery

from app.modules.cloning_report.repositories.detection_repository import (
    DetectionRepository,
    DetectionMapper,
)
from app.modules.cloning_report.domain.detection import Detection
from app.modules.cloning_report.data.query_builder import (
    BigQueryQueryBuilder,
    QueryParameters,
)
from app.modules.cloning_report.utils import get_logger
from app.utils import get_bigquery_client


logger = get_logger()


class BigQueryDetectionRepository(DetectionRepository):
    """Repository implementation for BigQuery data sources"""

    def __init__(
        self, project_id: str | None = None, credentials_path: str | None = None
    ):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.credentials_path = credentials_path or os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )
        self.client = None
        logger.info(f"BigQuery repository initialized for project: {self.project_id}")
        self.client = get_bigquery_client()

    def find_by_plate_and_period(
        self, plate: str, start_date: datetime, end_date: datetime
    ) -> list[Detection]:
        """Find detections for plate in time period from BigQuery"""
        if not self.client:
            raise RuntimeError("BigQuery client not initialized")

        logger.info(f"Loading detections for {plate} from BigQuery")

        params = QueryParameters(plate=plate, start_date=start_date, end_date=end_date)

        query, query_params = BigQueryQueryBuilder.build_vehicle_query(params)
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(name, param_type, value)
                for name, param_type, value in query_params
            ]
        )
        df = self.client.query(query, job_config=job_config).to_dataframe()

        logger.info(f"Found {len(df)} detections for {plate}")
        return DetectionMapper.dataframe_to_detections(df)

    def test_connection(self) -> bool:
        """Test BigQuery connection"""
        try:
            if not self.client:
                return False

            test_query = "SELECT 1 AS test_value"
            result = self.client.query(test_query).to_dataframe()
            return len(result) == 1 and result["test_value"].iloc[0] == 1

        except Exception:
            logger.exception("BigQuery connection test failed")
            return False
        