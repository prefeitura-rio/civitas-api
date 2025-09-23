"""Async application services for cloning detection"""
import asyncio
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from ..container import Container, get_container
from ..repositories.async_bigquery_detection_repository import AsyncBigQueryDetectionRepository, AsyncDetectionRepositoryFactory
from ..repositories.detection_repository import DetectionMapper

from ..domain.entities import CloningReport
from ..report import ClonagemReportGenerator
from ..utils import get_logger

logger = get_logger()


class AsyncCloningReportService:
    """Async service for cloning detection using Repository pattern with global BigQuery client"""
    
    def __init__(self, executor: Optional[ThreadPoolExecutor] = None):
        """
        Initialize async cloning report service
        
        Args:
            executor: Optional thread pool executor for BigQuery operations
        """
        self.executor = executor or ThreadPoolExecutor(max_workers=4)
        self._repository = None
    
    @property
    def repository(self) -> AsyncBigQueryDetectionRepository:
        """Lazy initialization of async BigQuery repository"""
        if self._repository is None:
            self._repository = AsyncDetectionRepositoryFactory.create_async_bigquery_repository(self.executor)
        return self._repository
    
    async def execute(self, plate: str, date_start: datetime, date_end: datetime, 
                     output_dir: str = "report", project_id: Optional[str] = None, 
                     credentials_path: Optional[str] = None) -> CloningReport:
        """
        Execute cloning detection asynchronously with flexible data source selection
        
        Args:
            plate: Vehicle plate to analyze
            date_start: Start date for analysis
            date_end: End date for analysis
            output_dir: Directory to save the report
            project_id: BigQuery project ID (optional, uses global client)
            credentials_path: BigQuery credentials path (optional, uses global client)
            
        Returns:
            CloningReport: Complete cloning analysis report
        """
        logger.info(f"Executing async cloning detection for plate {plate}")
        
        try:
            # Test connection first
            if not await self.repository.test_connection():
                logger.warning("BigQuery connection failed, this might cause issues")
            
            # Load detections asynchronously
            detections = await self.repository.find_by_plate_and_period(plate, date_start, date_end)
            df = DetectionMapper.detections_to_dataframe(detections)
            
            # Generate report (this part can also be made async if needed)
            generator = ClonagemReportGenerator(df, plate, date_start, date_end)
            report_path = await self._generate_report_async(generator, plate, output_dir)
            
            return self._create_report_entity(generator, plate, date_start, date_end, report_path)
            
        except Exception as e:
            logger.error(f"Async cloning detection failed: {str(e)}")
            raise
    
    async def _generate_report_async(self, generator: ClonagemReportGenerator, 
                                   plate: str, output_dir: str) -> str:
        """Generate report asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._generate_report_sync,
            generator,
            plate,
            output_dir
        )
    
    def _generate_report_sync(self, generator: ClonagemReportGenerator, 
                            plate: str, output_dir: str) -> str:
        """Generate report synchronously (runs in thread pool)"""
        try:
            report_path = generator.generate_report(output_dir)
            logger.info(f"Report generated: {report_path}")
            return report_path
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            raise
    
    def _create_report_entity(self, generator: ClonagemReportGenerator, 
                            plate: str, date_start: datetime, date_end: datetime, 
                            report_path: str) -> CloningReport:
        """Create CloningReport entity from generator results"""
        return CloningReport(
            plate=plate,
            start_date=date_start,
            end_date=date_end,
            report_path=report_path,
            total_detections=len(generator.df),
            suspicious_pairs=generator.get_suspicious_pairs(),
            analysis_summary=generator.get_analysis_summary()
        )
    
    async def close(self):
        """Close the service and cleanup resources"""
        if self._repository:
            await self._repository.close()
        if self.executor:
            self.executor.shutdown(wait=True)
        logger.info("Async cloning report service closed")


# Dependency injection for async service
def get_async_cloning_service() -> AsyncCloningReportService:
    """Create new async cloning service instance (no global state)"""
    return AsyncCloningReportService()


def get_async_cloning_service_with_executor(executor: ThreadPoolExecutor) -> AsyncCloningReportService:
    """Create async cloning service with custom executor"""
    return AsyncCloningReportService(executor=executor)
