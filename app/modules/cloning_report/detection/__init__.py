# -*- coding: utf-8 -*-
"""
detection package — Clean detection pipeline
-------------------------------------------
Refactored detection components following SOLID principles
"""

from .validation import DetectionValidator
from .preprocessing import DetectionPreprocessor
from .pair_detection import PairDetector
from .parallel_detection import ParallelPairDetector, DetectionPerformanceTracker
from .adaptive_detection import AdaptiveDetector, HighPerformanceDetector
from .map_generation import MapGenerator
from .daily_processing import DailyProcessor
from .pipeline import DetectionPipeline

__all__ = [
    'DetectionValidator', 'DetectionPreprocessor', 'PairDetector',
    'ParallelPairDetector', 'DetectionPerformanceTracker',
    'AdaptiveDetector', 'HighPerformanceDetector',
    'MapGenerator', 'DailyProcessor', 'DetectionPipeline'
]