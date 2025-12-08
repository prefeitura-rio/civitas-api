from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from .repositories.detection_repository import DetectionRepository
from .repositories.repository_factory import DetectionRepositoryFactory
from .repositories.async_bigquery_detection_repository import (
    AsyncBigQueryDetectionRepository,
    AsyncDetectionRepositoryFactory,
)


@dataclass
class Container:
    detection_repository: DetectionRepository
    async_detection_repository: AsyncBigQueryDetectionRepository | None = None
    executor: ThreadPoolExecutor | None = None


def get_container():
    """Get container with default repository"""
    return Container(
        detection_repository=DetectionRepositoryFactory.create_repository()
    )


def get_async_container(executor: ThreadPoolExecutor | None = None):
    """Get container with async BigQuery repository using global BigQuery client"""
    if executor is None:
        executor = ThreadPoolExecutor(max_workers=4)

    async_repo = AsyncDetectionRepositoryFactory.create_async_bigquery_repository(
        executor
    )

    return Container(
        detection_repository=DetectionRepositoryFactory.create_repository(),
        async_detection_repository=async_repo,
        executor=executor,
    )
