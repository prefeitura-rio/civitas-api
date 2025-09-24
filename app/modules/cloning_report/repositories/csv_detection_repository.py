"""CSV implementation of detection repository"""

from datetime import datetime
from pathlib import Path
import pandas as pd

from app.modules.cloning_report.repositories.detection_repository import (
    DetectionRepository,
    DetectionMapper,
)
from app.modules.cloning_report.domain.detection import Detection
from app.modules.cloning_report.utils import get_logger


logger = get_logger()


class CSVDetectionRepository(DetectionRepository):
    """Repository implementation for CSV data sources"""

    def __init__(self, data_directory: str = "dados_placas"):
        self.data_directory = Path(data_directory)
        logger.info(f"CSV repository initialized: {self.data_directory}")

    def find_by_plate_and_period(
        self, plate: str, start_date: datetime, end_date: datetime
    ) -> list[Detection]:
        """Find detections for plate in time period from CSV"""
        csv_path = self.data_directory / f"{plate}.csv"

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        logger.info(f"Loading detections for {plate} from CSV")

        df = pd.read_csv(csv_path)
        df = self._normalize_columns(df)
        df = self._filter_by_date_range(df, start_date, end_date)

        return DetectionMapper.dataframe_to_detections(df)

    def test_connection(self) -> bool:
        """Test if CSV directory exists"""
        return self.data_directory.exists() and self.data_directory.is_dir()

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names for consistency"""
        column_mapping = {
            "data_hora": "datahora",
            "DataHora": "datahora",
            "timestamp": "datahora",
            "license_plate": "placa",
            "plate": "placa",
            "lat": "latitude",
            "lon": "longitude",
            "lng": "longitude",
            "speed": "velocidade",
            "codigo_equipamento": "codcet",
        }
        return df.rename(columns=column_mapping)

    def _filter_by_date_range(
        self, df: pd.DataFrame, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Filter DataFrame by date range"""
        if "datahora" not in df.columns:
            return df

        df["datahora"] = pd.to_datetime(df["datahora"], errors="coerce")
        mask = (df["datahora"] >= start_date) & (df["datahora"] <= end_date)
        return df[mask]
