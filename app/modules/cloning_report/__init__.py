"""
Civitas Cloning Detector - License Plate Cloning Detection System
================================================================

A comprehensive system for detecting potential vehicle license plate cloning
based on impossible travel speeds between detection points.

Usage:
    # New service-oriented API (recommended)
    from civitas_cloning_detector import CloningReportService
    from datetime import datetime
    
    report = CloningReportService.execute(
        plate="ABC1234", 
        date_start=datetime(2024, 1, 1),
        date_end=datetime(2024, 1, 31)
    )

Author: Civitas Team
License: MIT
Python: 3.12+
"""

__version__ = "2.0.0"
__author__ = "Civitas Team"
__email__ = "tech@civitas.rio"

# New service layer (recommended API)
from .application.services import CloningReportService

# Domain entities
from .domain.entities import CloningReport, SuspiciousPair, Detection

# Main application exports (legacy API)
from .detection import DetectionPipeline
from .clustering import ClusteringPipeline
from .analytics import (
    compute_clonagem_kpis,
    compute_bairro_pair_stats,
    plot_bairro_pair_stats,
    compute_hourly_profile,
    plot_hourly_histogram
)
from .report.clonagem_report_generator.generator import ClonagemReportGenerator

# Utility exports
from .utils import (
    haversine_km, 
    ensure_dir, 
    VMAX_KMH, 
    BLUE_LIGHT, 
    BLUE_DARK,
    abbreviate_local
)

__all__ = [
    # Service layer (new API)
    'CloningReportService',
    
    # Domain entities
    'CloningReport',
    'SuspiciousPair',
    'Detection',
    
    # Core pipeline classes (legacy API)
    'DetectionPipeline',
    'ClusteringPipeline', 
    'ClonagemReportGenerator',
    
    # Analytics
    'compute_clonagem_kpis',
    'compute_bairro_pair_stats',
    'plot_bairro_pair_stats', 
    'compute_hourly_profile',
    'plot_hourly_histogram',
    
    # Utilities
    'haversine_km',
    'ensure_dir',
    'abbreviate_local',
    
    # Constants
    'VMAX_KMH',
    'BLUE_LIGHT', 
    'BLUE_DARK',
    
    # Metadata
    '__version__',
    '__author__',
    '__email__',
]
