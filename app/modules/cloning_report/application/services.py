"""Application services for cloning detection"""

from datetime import datetime
import pandas as pd

from app.modules.cloning_report.container import Container, get_container

from app.modules.cloning_report.domain.entities import CloningReport
from app.modules.cloning_report.report import ClonagemReportGenerator
from app.modules.cloning_report.repositories import DetectionMapper
from app.modules.cloning_report.utils import get_logger

logger = get_logger()


class CloningReportService:
    """Clean service for cloning detection using Repository pattern"""

    @staticmethod
    def execute(
        plate: str,
        date_start: datetime,
        date_end: datetime,
        container: Container | None = None,
        project_id: str | None = None,
        credentials_path: str | None = None,
    ) -> CloningReport:
        """Execute cloning detection with flexible data source selection"""
        container = container or get_container()
        logger.info(f"Executing cloning detection for plate {plate}")

        repository = container.detection_repository
        detections = CloningReportService._load_detections(
            repository, plate, date_start, date_end
        )
        df = DetectionMapper.detections_to_dataframe(detections)

        # Convert to UTC timestamp, handling both naive and timezone-aware datetimes
        if date_start.tzinfo is None:
            periodo_inicio = pd.Timestamp(date_start, tz="UTC")
        else:
            periodo_inicio = pd.Timestamp(date_start).tz_convert("UTC")

        if date_end.tzinfo is None:
            periodo_fim = pd.Timestamp(date_end, tz="UTC")
        else:
            periodo_fim = pd.Timestamp(date_end).tz_convert("UTC")
        generator = ClonagemReportGenerator(df, plate, periodo_inicio, periodo_fim)
        report_path = CloningReportService._generate_report(generator)

        return CloningReportService._create_report_entity(
            generator, plate, date_start, date_end, report_path
        )

    @staticmethod
    def _load_detections(
        repository, plate: str, date_start: datetime, date_end: datetime
    ):
        """Load detections with automatic fallback"""
        if not repository.test_connection():
            raise RuntimeError("Detection repository connection failed")

        detections = repository.find_by_plate_and_period(plate, date_start, date_end)
        logger.info(f"Loaded {len(detections)} detections")
        return detections

    @staticmethod
    def _generate_report(generator: ClonagemReportGenerator) -> str:
        """Generate PDF report and return path"""
        return str(generator.generate())

    @staticmethod
    def _create_report_entity(
        generator: ClonagemReportGenerator,
        plate: str,
        date_start: datetime,
        date_end: datetime,
        report_path: str,
    ) -> CloningReport:
        """Create domain entity from generator results"""
        return CloningReport(
            plate=plate,
            period_start=date_start,
            period_end=date_end,
            suspicious_pairs=[],  # TODO: convert from generator.results
            total_detections=generator.total_deteccoes,
            report_path=report_path,
        )


class RepositoryTestService:
    """Service for testing repository connections"""

    @staticmethod
    def test_repositories() -> dict:
        """Test all available repositories"""
        results = {}

        try:
            from app.modules.cloning_report.repositories.bigquery_detection_repository import (
                BigQueryDetectionRepository,
            )

            bq_repo = BigQueryDetectionRepository()
            results["bigquery"] = {
                "available": bq_repo.test_connection(),
                "type": "Google BigQuery",
                "description": "Production BigQuery database",
            }
        except Exception as e:
            results["bigquery"] = {"available": False, "error": str(e)}

        return results
