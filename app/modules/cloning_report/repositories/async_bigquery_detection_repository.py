"""Async BigQuery implementation of detection repository"""

import asyncio
from datetime import datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

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


class AsyncBigQueryDetectionRepository(DetectionRepository):
    """Async repository implementation for BigQuery data sources using global client"""

    def __init__(self, executor: ThreadPoolExecutor | None = None):
        """
        Initialize async BigQuery repository using global client

        Args:
            executor: Optional thread pool executor for running sync BigQuery operations
        """
        self.executor = executor or ThreadPoolExecutor(max_workers=4)
        self._client = None
        logger.info("Async BigQuery repository initialized with global client")

    @property
    def client(self):
        """Lazy initialization of BigQuery client using global instance"""
        if self._client is None:
            self._client = get_bigquery_client()
        return self._client

    async def find_by_plate_and_period(
        self, plate: str, start_date: datetime, end_date: datetime
    ) -> list[Detection]:
        """Find detections for plate in time period from BigQuery asynchronously"""
        logger.info(f"Loading detections for {plate} from BigQuery (async)")

        params = QueryParameters(plate=plate, start_date=start_date, end_date=end_date)

        query = BigQueryQueryBuilder.build_vehicle_query(params)

        # Run the BigQuery operation in a thread pool
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(self.executor, self._execute_query, query)

        logger.info(f"Found {len(df)} detections for {plate}")
        return DetectionMapper.dataframe_to_detections(df)

    def _execute_query(self, query: str) -> pd.DataFrame:
        """Execute BigQuery query synchronously (runs in thread pool)"""
        try:
            query_job = self.client.query(query)
            return query_job.to_dataframe()
        except Exception as e:
            logger.traceback(f"BigQuery query execution failed: {str(e)}")
            raise

    async def test_connection(self) -> bool:
        """Test BigQuery connection asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, self._test_connection_sync
            )
            return result
        except Exception as e:
            logger.traceback(f"Async BigQuery connection test failed: {str(e)}")
            return False

    def _test_connection_sync(self) -> bool:
        """Test BigQuery connection synchronously (runs in thread pool)"""
        try:
            test_query = "SELECT 1 AS test_value"
            result = self.client.query(test_query).to_dataframe()
            return len(result) == 1 and result["test_value"].iloc[0] == 1
        except Exception as e:
            logger.traceback(f"BigQuery connection test failed: {str(e)}")
            return False

    async def close(self):
        """Close the thread pool executor"""
        if self.executor:
            self.executor.shutdown(wait=True)
            logger.info("Async BigQuery repository executor closed")


class AsyncDetectionRepositoryFactory:
    """Factory for creating async detection repositories"""

    @staticmethod
    def create_async_bigquery_repository(
        executor: ThreadPoolExecutor | None = None,
    ) -> AsyncBigQueryDetectionRepository:
        """Create async BigQuery repository using global client"""
        return AsyncBigQueryDetectionRepository(executor=executor)

    @staticmethod
    def create_repository_with_global_client() -> AsyncBigQueryDetectionRepository:
        """Create async BigQuery repository with default executor"""
        return AsyncBigQueryDetectionRepository()
