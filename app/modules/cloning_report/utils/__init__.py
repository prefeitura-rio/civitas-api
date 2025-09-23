# -*- coding: utf-8 -*-
"""
utils package - Clean architecture utilities
-------------------------------------------
Organized by single responsibility principle with backward compatibility
"""

from .constants import BLUE_LIGHT, BLUE_DARK, VMAX_KMH
from .filesystem import FileSystemService
from .datetime import DateTimeService  
from .geography import GeographyService
from .text import TextFormatter
from .graph import GraphAnalyzer
from .logging import get_logger, configure_logging, LogLevel
from .progress import ProgressTracker, ScreenshotProgressTracker

# Backward compatibility - expose the original function names
def ensure_dir(path):
    return FileSystemService.ensure_directory(path)

def haversine_km(lat1, lon1, lat2, lon2):
    return GeographyService.haversine_distance(lat1, lon1, lat2, lon2)

def to_datetime_utc(x):
    return DateTimeService.to_utc_timestamp(x)

def strftime_safe(ts, fmt="%d/%m/%Y %H:%M:%S"):
    return DateTimeService.format_safely(ts, fmt)

def abbreviate_local(text):
    return TextFormatter.abbreviate_location(text)

def violations(labels, edges):
    return GraphAnalyzer.count_violations(labels, edges)

__all__ = [
    'BLUE_LIGHT', 'BLUE_DARK', 'VMAX_KMH',
    'FileSystemService', 'DateTimeService', 'GeographyService', 
    'TextFormatter', 'GraphAnalyzer',
    'get_logger', 'configure_logging', 'LogLevel',
    'ProgressTracker', 'ScreenshotProgressTracker',
    'ensure_dir', 'haversine_km', 'to_datetime_utc', 'strftime_safe',
    'abbreviate_local', 'violations'
]