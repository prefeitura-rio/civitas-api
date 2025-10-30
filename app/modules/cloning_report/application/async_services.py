"""Async application services for cloning detection"""

import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

from app.modules.cloning_report.container import get_async_container
from app.modules.cloning_report.repositories.async_bigquery_detection_repository import (
    AsyncBigQueryDetectionRepository,
)
from app.modules.cloning_report.repositories.detection_repository import DetectionMapper

from app.modules.cloning_report.domain.entities import CloningReport
from app.modules.cloning_report.report import (
    ClonagemReportGenerator,
    ClonagemReportWeasyGenerator,
)
from app.modules.cloning_report.utils import get_logger

logger = get_logger()


class AsyncCloningReportService:
    """Async service for cloning detection using Repository pattern with global BigQuery client"""

    def __init__(self, executor: ThreadPoolExecutor | None = None):
        """
        Initialize async cloning report service

        Args:
            executor: Optional thread pool executor for BigQuery operations
        """
        self.executor = executor or ThreadPoolExecutor(max_workers=4)
        self._repository = None
        self._container = None

    @property
    def repository(self) -> AsyncBigQueryDetectionRepository:
        """Lazy initialization of async BigQuery repository using container"""
        if self._repository is None:
            if self._container is None:
                self._container = get_async_container(self.executor)
            self._repository = self._container.async_detection_repository
        return self._repository

    async def execute(
        self,
        plate: str,
        date_start: datetime,
        date_end: datetime,
        output_dir: str = "report",
        project_id: str | None = None,
        credentials_path: str | None = None,
        report_id: str | None = None,
        renderer: str = "fpdf",
    ) -> CloningReport:
        """
        Execute cloning detection asynchronously with flexible data source selection

        Args:
            plate: Vehicle plate to analyze
            date_start: Start date for analysis
            date_end: End date for analysis
            output_dir: Directory to save the report
            project_id: BigQuery project ID (optional, uses global client)
            credentials_path: BigQuery credentials path (optional, uses global client)
            report_id: External report ID to use (optional, generates one if not provided)

        Returns:
            CloningReport: Complete cloning analysis report
        """
        logger.info(f"Executing async cloning detection for plate {plate}")

        try:
            if not await self.repository.test_connection():
                logger.warning("BigQuery connection failed, this might cause issues")

            detections = await self.repository.find_by_plate_and_period(
                plate, date_start, date_end
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
            generator_cls = self._resolve_generator(renderer)
            generator = generator_cls(df, plate, periodo_inicio, periodo_fim, report_id)
            report_path = self._generate_report_sync(generator, plate, output_dir)

            return self._create_report_entity(
                generator, plate, date_start, date_end, report_path
            )

        except Exception:
            logger.exception("Async cloning detection failed")
            raise

    async def _generate_report_async(
        self, generator: ClonagemReportGenerator, plate: str, output_dir: str
    ) -> str:
        """Generate report asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._generate_report_sync, generator, plate, output_dir
        )

    def _generate_report_sync(
        self, generator: ClonagemReportGenerator, plate: str, output_dir: str
    ) -> str:
        """Generate report synchronously (runs in thread pool)"""
        try:
            import os

            os.makedirs(output_dir, exist_ok=True)
            report_filename = f"relatorio_clonagem_{plate}_{generator.periodo_inicio.strftime('%Y%m%d')}_{generator.periodo_fim.strftime('%Y%m%d')}.pdf"
            report_path = os.path.join(output_dir, report_filename)

            report_path = generator.generate(report_path)
            logger.info(f"Report generated: {report_path}")
            return report_path
        except Exception:
            logger.exception("Report generation failed")
            raise

    def _resolve_generator(self, renderer: str):
        """Select report generator implementation"""
        mapping = {
            "fpdf": ClonagemReportGenerator,
            "weasy": ClonagemReportWeasyGenerator,
        }
        return mapping.get((renderer or "fpdf").lower(), ClonagemReportGenerator)

    def _create_report_entity(
        self,
        generator: ClonagemReportGenerator,
        plate: str,
        date_start: datetime,
        date_end: datetime,
        report_path: str,
    ) -> CloningReport:
        """Create CloningReport entity from generator results"""
        from app.modules.cloning_report.domain.entities import SuspiciousPair, Detection

        suspicious_pairs = []
        pairs_data = generator.get_suspicious_pairs()

        for pair_data in pairs_data:
            try:
                origin = Detection(
                    plate=plate,
                    timestamp=pd.to_datetime(pair_data["Data"]),
                    latitude=float(pair_data["latitude_1"]),
                    longitude=float(pair_data["longitude_1"]),
                    location=str(pair_data["Origem"]),
                )

                destination = Detection(
                    plate=plate,
                    timestamp=pd.to_datetime(pair_data["DataDestino"]),
                    latitude=float(pair_data["latitude_2"]),
                    longitude=float(pair_data["longitude_2"]),
                    location=str(pair_data["Destino"]),
                )

                suspicious_pair = SuspiciousPair(
                    origin=origin,
                    destination=destination,
                    distance_km=float(pair_data["Km"]),
                    time_seconds=float(pair_data["s"]),
                    speed_kmh=float(pair_data["Km/h"]),
                )

                suspicious_pairs.append(suspicious_pair)

            except Exception as e:
                logger.warning(f"Failed to convert pair data: {e}")
                continue

        return CloningReport(
            plate=plate,
            period_start=date_start,
            period_end=date_end,
            report_path=report_path,
            total_detections=len(generator.df),
            suspicious_pairs=suspicious_pairs,
        )

    async def close(self):
        """Close the service and cleanup resources"""
        if self._repository:
            await self._repository.close()
        if self._container and self._container.executor:
            self._container.executor.shutdown(wait=True)
        elif self.executor:
            self.executor.shutdown(wait=True)
        logger.info("Async cloning report service closed")


def get_async_cloning_service() -> AsyncCloningReportService:
    """Create new async cloning service instance (no global state)"""
    return AsyncCloningReportService()


def get_async_cloning_service_with_executor(
    executor: ThreadPoolExecutor,
) -> AsyncCloningReportService:
    """Create async cloning service with custom executor"""
    return AsyncCloningReportService(executor=executor)
