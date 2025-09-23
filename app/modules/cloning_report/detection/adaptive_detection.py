"""
adaptive_detection.py - Adaptive detection with intelligent parallel/sequential selection
---------------------------------------------------------------------------------------
Automatically chooses the best detection method based on dataset characteristics
"""
import pandas as pd
import time
from typing import Dict, Any, Optional
import multiprocessing

from ..utils import get_logger
from .pair_detection import PairDetector
from .parallel_detection import ParallelPairDetector


logger = get_logger()


class AdaptiveDetector:
    """Intelligently chooses between sequential and parallel detection"""
    
    # Performance thresholds for switching to parallel processing
    MIN_RECORDS_FOR_PARALLEL = 5000      # Minimum records to consider parallel
    COMPLEXITY_THRESHOLD = 1000000       # Records² threshold for complex datasets
    CHUNK_OVERHEAD_FACTOR = 0.8          # Process startup overhead factor
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(multiprocessing.cpu_count(), 8)
        self.performance_cache = {}  # Cache performance characteristics
        
    def find_suspicious_pairs(self, df: pd.DataFrame, speed_limit: float) -> pd.DataFrame:
        """Adaptively choose the best detection method"""
        dataset_complexity = self._analyze_dataset_complexity(df)
        
        detection_method = self._choose_detection_method(dataset_complexity)
        
        logger.info(f"Using {detection_method} detection for {len(df)} records")
        
        if detection_method == "parallel":
            detector = ParallelPairDetector(self.max_workers)
            return detector.find_suspicious_pairs(df, speed_limit)
        else:
            return PairDetector.find_suspicious_pairs(df, speed_limit)
    
    def _analyze_dataset_complexity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze dataset to determine computational complexity"""
        num_records = len(df)
        num_pairs = num_records - 1 if num_records > 1 else 0
        
        # Estimate computational complexity
        # Each pair requires: distance calculation, time diff, speed calculation
        estimated_operations = num_pairs * 10  # Rough estimate
        
        # Check for data density (more unique coordinates = more complex)
        unique_coords = len(df[['latitude', 'longitude']].drop_duplicates())
        coord_diversity = unique_coords / num_records if num_records > 0 else 0
        
        # Time span analysis
        if 'datahora' in df.columns:
            df_time = df.copy()
            df_time['datahora'] = pd.to_datetime(df_time['datahora'], errors='coerce')
            time_span_hours = (df_time['datahora'].max() - df_time['datahora'].min()).total_seconds() / 3600
        else:
            time_span_hours = 0
        
        complexity = {
            'num_records': num_records,
            'num_pairs': num_pairs,
            'estimated_operations': estimated_operations,
            'coord_diversity': coord_diversity,
            'time_span_hours': time_span_hours,
            'complexity_score': self._calculate_complexity_score(num_records, coord_diversity, time_span_hours)
        }
        
        logger.debug(f"Dataset complexity: {complexity}")
        return complexity
    
    def _calculate_complexity_score(self, num_records: int, coord_diversity: float, time_span: float) -> float:
        """Calculate overall complexity score"""
        # Base score from number of records (quadratic growth)
        base_score = num_records ** 1.5
        
        # Multiply by coordinate diversity (more unique locations = more complex)
        diversity_factor = 1 + coord_diversity
        
        # Factor in time span (longer periods may have more suspicious patterns)
        time_factor = 1 + (time_span / 24)  # Normalize by days
        
        return base_score * diversity_factor * time_factor
    
    def _choose_detection_method(self, complexity: Dict[str, Any]) -> str:
        """Choose detection method based on complexity analysis"""
        num_records = complexity['num_records']
        complexity_score = complexity['complexity_score']
        
        # Always use sequential for very small datasets
        if num_records < 100:
            return "sequential"
        
        # Use parallel for very large datasets
        if num_records >= self.MIN_RECORDS_FOR_PARALLEL:
            return "parallel"
        
        # For medium datasets, use complexity score
        if complexity_score >= self.COMPLEXITY_THRESHOLD:
            return "parallel"
        
        return "sequential"
    
    def benchmark_and_cache(self, df: pd.DataFrame, speed_limit: float) -> Dict[str, Any]:
        """Benchmark both methods and cache results for similar datasets"""
        dataset_key = self._create_dataset_key(df)
        
        if dataset_key in self.performance_cache:
            logger.debug(f"Using cached performance data for dataset type")
            return self.performance_cache[dataset_key]
        
        logger.info(f"Benchmarking detection methods for dataset caching")
        
        # Test sequential
        start_time = time.time()
        seq_result = PairDetector.find_suspicious_pairs(df, speed_limit)
        seq_time = time.time() - start_time
        
        # Test parallel (only if dataset is large enough)
        if len(df) >= 200:
            detector = ParallelPairDetector(self.max_workers)
            start_time = time.time()
            par_result = detector.find_suspicious_pairs(df, speed_limit)
            par_time = time.time() - start_time
        else:
            par_result = seq_result
            par_time = seq_time * 2  # Assume parallel is slower for small datasets
        
        # Cache results
        performance_data = {
            'sequential_time': seq_time,
            'parallel_time': par_time,
            'speedup_factor': seq_time / par_time if par_time > 0 else 0,
            'recommended_method': 'parallel' if par_time < seq_time else 'sequential',
            'dataset_size': len(df),
            'pairs_found': len(seq_result)
        }
        
        self.performance_cache[dataset_key] = performance_data
        logger.info(f"Cached performance: {performance_data['recommended_method']} recommended")
        
        return performance_data
    
    def _create_dataset_key(self, df: pd.DataFrame) -> str:
        """Create a key for caching based on dataset characteristics"""
        size_bucket = (len(df) // 100) * 100  # Round to nearest 100
        return f"size_{size_bucket}"


class HighPerformanceDetector:
    """Optimized detector for large-scale processing"""
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(multiprocessing.cpu_count(), 8)
        self.adaptive_detector = AdaptiveDetector(max_workers)
        
    def detect_with_optimization(self, df: pd.DataFrame, speed_limit: float,
                                force_method: Optional[str] = None) -> Dict[str, Any]:
        """Detect with automatic optimization and performance tracking"""
        start_time = time.time()
        
        if force_method == "parallel":
            detector = ParallelPairDetector(self.max_workers)
            result = detector.find_suspicious_pairs(df, speed_limit)
            method_used = "parallel"
        elif force_method == "sequential":
            result = PairDetector.find_suspicious_pairs(df, speed_limit)
            method_used = "sequential"
        else:
            # Use adaptive selection
            result = self.adaptive_detector.find_suspicious_pairs(df, speed_limit)
            method_used = "adaptive"
        
        total_time = time.time() - start_time
        
        logger.info(f"Detection completed using {method_used} method: {len(result)} pairs in {total_time:.2f}s")
        
        return {
            'dataframe': result,
            'method_used': method_used,
            'processing_time': total_time,
            'pairs_found': len(result),
            'records_processed': len(df),
            'performance_ratio': len(df) / total_time if total_time > 0 else 0
        }