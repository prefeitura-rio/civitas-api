"""Repository pattern for detection data access"""

from abc import ABC, abstractmethod
from datetime import datetime
import pandas as pd

from app.modules.cloning_report.domain.detection import Detection


class DetectionRepository(ABC):
    """Abstract repository for vehicle detection data"""

    @abstractmethod
    def find_by_plate_and_period(
        self, plate: str, start_date: datetime, end_date: datetime
    ) -> list[Detection]:
        """Find all detections for a plate in time period"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if data source is accessible"""
        pass


class DetectionMapper:
    """Maps between DataFrame and domain entities"""

    @staticmethod
    def dataframe_to_detections(df: pd.DataFrame) -> list[Detection]:
        """Convert DataFrame to Detection entities"""
        detections = []
        for _, row in df.iterrows():
            detection = Detection(
                datetime=pd.to_datetime(row["datahora"], utc=True),
                plate=row["placa"],
                equipment_code=row["codcet"],
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                speed=float(row["velocidade"])
                if "velocidade" in row and pd.notna(row["velocidade"])
                else None,
                neighborhood=row.get("bairro", ""),
                locality=row.get("localidade", ""),
                street=row.get("logradouro", ""),
            )
            detections.append(detection)
        return detections

    @staticmethod
    def detections_to_dataframe(detections: list[Detection]) -> pd.DataFrame:
        """Convert Detection entities to DataFrame"""
        data = []
        for detection in detections:
            data.append(
                {
                    "datahora": detection.datetime,
                    "placa": detection.plate,
                    "codcet": detection.equipment_code,
                    "latitude": detection.latitude,
                    "longitude": detection.longitude,
                    "velocidade": detection.speed,
                    "bairro": detection.neighborhood,
                    "localidade": detection.locality,
                    "logradouro": detection.street,
                    "localidade_codcet": detection.location_display,
                }
            )
        return pd.DataFrame(data)
