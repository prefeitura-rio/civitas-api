from dataclasses import dataclass

from .repositories.csv_detection_repository import CSVDetectionRepository
from .repositories.detection_repository import DetectionRepository


@dataclass
class Container:
    detection_repository: DetectionRepository



def get_container():
    return Container(
        detection_repository=CSVDetectionRepository(data_directory="dados_placas")
    )
