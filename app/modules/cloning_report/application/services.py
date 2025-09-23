"""Application services for cloning detection"""
from datetime import datetime
from typing import Optional

from ..container import Container, get_container
from ..repositories.detection_repository import DetectionRepository

from ..domain.entities import CloningReport
from ..report import ClonagemReportGenerator
from ..repositories import DetectionRepositoryFactory, DetectionMapper
from ..utils import get_logger

logger = get_logger()

class CloningReportService:
    """Clean service for cloning detection using Repository pattern"""
    
    @staticmethod
    def execute(plate: str, date_start: datetime, date_end: datetime, 
                output_dir: str = "report", container: Container = get_container(),
                project_id: Optional[str] = None, 
                credentials_path: Optional[str] = None) -> CloningReport:
        """Execute cloning detection with flexible data source selection"""
        logger.info(f"Executing cloning detection for plate {plate}")

        repository = container.detection_repository
        detections = CloningReportService._load_detections(repository, plate, date_start, date_end)
        df = DetectionMapper.detections_to_dataframe(detections)
        
        generator = ClonagemReportGenerator(df, plate, date_start, date_end)
        report_path = CloningReportService._generate_report(generator, plate, output_dir)
        
        return CloningReportService._create_report_entity(generator, plate, date_start, date_end, report_path)
    
    
    @staticmethod
    def _load_detections(repository, plate: str, date_start: datetime, date_end: datetime):
        """Load detections with automatic fallback"""
        if not repository.test_connection():
            logger.warning("Repository connection failed, falling back to CSV")
            repository = DetectionRepositoryFactory.create_csv_repository()
        
        detections = repository.find_by_plate_and_period(plate, date_start, date_end)
        logger.info(f"Loaded {len(detections)} detections")
        return detections
    
    
    @staticmethod
    def _generate_report(generator: ClonagemReportGenerator, 
                        plate: str, output_dir: str) -> str:
        """Generate PDF report and return path"""
        return generator.generate(f'{output_dir}/{plate}.pdf')
    
    @staticmethod
    def _create_report_entity(generator: ClonagemReportGenerator, plate: str,
                             date_start: datetime, date_end: datetime, report_path: str) -> CloningReport:
        """Create domain entity from generator results"""
        return CloningReport(
            plate=plate,
            period_start=date_start,
            period_end=date_end,
            suspicious_pairs=[],  # TODO: convert from generator.results
            total_detections=generator.total_deteccoes,
            report_path=report_path
        )


class RepositoryTestService:
    """Service for testing repository connections"""
    
    @staticmethod
    def test_repositories() -> dict:
        """Test all available repositories"""
        results = {}
        
        try:
            csv_repo = DetectionRepositoryFactory.create_csv_repository()
            results['csv'] = {
                'available': csv_repo.test_connection(),
                'type': 'CSV Files',
                'description': 'Local CSV files for development'
            }
        except Exception as e:
            results['csv'] = {'available': False, 'error': str(e)}
        
        try:
            bq_repo = DetectionRepositoryFactory.create_repository("bigquery")
            results['bigquery'] = {
                'available': bq_repo.test_connection(),
                'type': 'Google BigQuery',
                'description': 'Production BigQuery database'
            }
        except Exception as e:
            results['bigquery'] = {'available': False, 'error': str(e)}
        
        return results
