from dataclasses import dataclass
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from .repositories.csv_detection_repository import CSVDetectionRepository
from .repositories.detection_repository import DetectionRepository
from .repositories.async_bigquery_detection_repository import AsyncBigQueryDetectionRepository, AsyncDetectionRepositoryFactory


@dataclass
class Container:
    detection_repository: DetectionRepository
    async_detection_repository: Optional[AsyncBigQueryDetectionRepository] = None
    executor: Optional[ThreadPoolExecutor] = None


def get_container():
    """Get container with CSV repository (for backward compatibility)"""
    return Container(
        detection_repository=CSVDetectionRepository(data_directory="dados_placas")
    )


def get_async_container(executor: Optional[ThreadPoolExecutor] = None):
    """Get container with async BigQuery repository using global BigQuery client"""
    if executor is None:
        executor = ThreadPoolExecutor(max_workers=4)
    
    async_repo = AsyncDetectionRepositoryFactory.create_async_bigquery_repository(executor)
    
    return Container(
        detection_repository=CSVDetectionRepository(data_directory="dados_placas"),  # Keep for compatibility
        async_detection_repository=async_repo,
        executor=executor
    )
