# -*- coding: utf-8 -*-
"""
pipeline.py — Main detection pipeline orchestrator
"""
from typing import Dict, Any
import pandas as pd
from ..utils import VMAX_KMH

from .validation import DetectionValidator
from .preprocessing import DetectionPreprocessor
from .pair_detection import PairDetector
from .parallel_detection import ParallelPairDetector
from .adaptive_detection import AdaptiveDetector, HighPerformanceDetector
from .map_generation import MapGenerator
from .daily_processing import DailyProcessor


class DetectionPipeline:
    """Orchestrates the complete cloning detection pipeline"""
    
    @staticmethod
    def detect_cloning(df: pd.DataFrame, plot: bool = True, 
                      speed_limit: float = VMAX_KMH, parallel: bool = True) -> Dict[str, Any]:
        """Execute complete cloning detection pipeline"""
        processed_data = DetectionPipeline._validate_and_preprocess(df)
        suspicious_pairs = DetectionPipeline._detect_suspicious_pairs(processed_data, speed_limit, parallel)
        html_path = DetectionPipeline._generate_maps(suspicious_pairs, processed_data, speed_limit, plot)
        return DetectionPipeline._create_results(suspicious_pairs, html_path, speed_limit)
    
    @staticmethod
    def detect_cloning_parallel(df: pd.DataFrame, plot: bool = True, 
                               speed_limit: float = VMAX_KMH, max_workers: int = None) -> Dict[str, Any]:
        """Execute cloning detection with explicit parallel processing"""
        processed_data = DetectionPipeline._validate_and_preprocess(df)
        parallel_detector = ParallelPairDetector(max_workers)
        suspicious_pairs = parallel_detector.find_suspicious_pairs(processed_data, speed_limit)
        html_path = DetectionPipeline._generate_maps(suspicious_pairs, processed_data, speed_limit, plot)
        return DetectionPipeline._create_results(suspicious_pairs, html_path, speed_limit)
    
    @staticmethod
    def _detect_suspicious_pairs(df: pd.DataFrame, speed_limit: float, parallel: bool) -> pd.DataFrame:
        """Detect suspicious pairs using adaptive method selection"""
        if parallel:
            detector = AdaptiveDetector()
            return detector.find_suspicious_pairs(df, speed_limit)
        else:
            return PairDetector.find_suspicious_pairs(df, speed_limit)
    
    @staticmethod
    def detect_cloning_optimized(df: pd.DataFrame, plot: bool = True,
                               speed_limit: float = VMAX_KMH) -> Dict[str, Any]:
        """Execute cloning detection with full optimization and performance tracking"""
        processed_data = DetectionPipeline._validate_and_preprocess(df)
        
        hp_detector = HighPerformanceDetector()
        detection_result = hp_detector.detect_with_optimization(processed_data, speed_limit)
        
        suspicious_pairs = detection_result['dataframe']
        html_path = DetectionPipeline._generate_maps(suspicious_pairs, processed_data, speed_limit, plot)
        
        results = DetectionPipeline._create_results(suspicious_pairs, html_path, speed_limit)
        results['performance_metrics'] = {
            'detection_method': detection_result['method_used'],
            'processing_time': detection_result['processing_time'],
            'performance_ratio': detection_result['performance_ratio']
        }
        
        return results
    
    @staticmethod
    def _generate_maps(suspicious_pairs: pd.DataFrame, processed_data: pd.DataFrame, 
                      speed_limit: float, plot: bool) -> str:
        """Generate maps if plotting is enabled"""
        if not plot:
            return ""
        return MapGenerator.generate_detection_map(suspicious_pairs, processed_data, speed_limit)
    
    @staticmethod
    def _validate_and_preprocess(df: pd.DataFrame) -> pd.DataFrame:
        """Validate input and preprocess data"""
        DetectionValidator.validate_dataframe(df)
        return DetectionPreprocessor.prepare_dataframe(df)
    
    @staticmethod
    def _create_results(suspicious_pairs: pd.DataFrame, html_path: str, speed_limit: float) -> Dict[str, Any]:
        """Create final results dictionary"""
        daily_data = DetectionPipeline._process_daily_data(suspicious_pairs, speed_limit)
        return DetectionPipeline._build_results_dictionary(suspicious_pairs, html_path, daily_data)
    
    @staticmethod
    def _process_daily_data(suspicious_pairs: pd.DataFrame, speed_limit: float) -> Dict[str, Any]:
        """Process daily figures, tables and tracks"""
        daily_figures = DailyProcessor.create_daily_figures(suspicious_pairs)
        daily_tables = DailyProcessor.create_daily_tables(suspicious_pairs)
        track_tables = DailyProcessor.create_track_tables(suspicious_pairs, speed_limit)
        return {'figures': daily_figures, 'tables': daily_tables, 'tracks': track_tables}
    
    @staticmethod
    def _build_results_dictionary(suspicious_pairs: pd.DataFrame, html_path: str, daily_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build final results dictionary"""
        return {
            'dataframe': suspicious_pairs,
            'html_file': html_path,
            'daily_figures': daily_data['figures'],
            'daily_tables': daily_data['tables'],
            'daily_track_tables': daily_data['tracks'],
            'kpis': {}, 
        }
