"""
detection package - Clean detection pipeline
-------------------------------------------
Refactored detection components following SOLID principles
"""

from app.modules.cloning_report.detection.validation import DetectionValidator
from app.modules.cloning_report.detection.preprocessing import DetectionPreprocessor
from app.modules.cloning_report.detection.pair_detection import PairDetector
from app.modules.cloning_report.detection.parallel_detection import (
    ParallelPairDetector,
    DetectionPerformanceTracker,
)
from app.modules.cloning_report.detection.adaptive_detection import (
    AdaptiveDetector,
    HighPerformanceDetector,
)
from app.modules.cloning_report.detection.map_generation import MapGenerator
from app.modules.cloning_report.detection.daily_processing import DailyProcessor
from app.modules.cloning_report.detection.pipeline import DetectionPipeline

__all__ = [
    "DetectionValidator",
    "DetectionPreprocessor",
    "PairDetector",
    "ParallelPairDetector",
    "DetectionPerformanceTracker",
    "AdaptiveDetector",
    "HighPerformanceDetector",
    "MapGenerator",
    "DailyProcessor",
    "DetectionPipeline",
]
