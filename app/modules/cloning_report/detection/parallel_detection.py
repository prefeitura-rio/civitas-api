"""
parallel_detection.py - High-performance parallel detection pipeline
------------------------------------------------------------------
Implements chunk-based threading for suspicious pair detection
"""

import pandas as pd
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from dataclasses import dataclass
import time

from app.modules.cloning_report.utils import get_logger
from app.modules.cloning_report.detection.pair_detection import PairDetector


logger = get_logger()


@dataclass
class DetectionChunk:
    """Represents a chunk of data for parallel processing"""

    chunk_id: int
    data: pd.DataFrame
    speed_limit: float
    overlap_rows: int = 1  # Rows to overlap with next chunk


@dataclass
class ChunkResult:
    """Result from processing a detection chunk"""

    chunk_id: int
    pairs: list[dict[str, Any]]
    processing_time: float
    pairs_found: int


class ParallelPairDetector:
    """High-performance parallel pair detector"""

    def __init__(self, max_workers: int | None = None):
        self.max_workers = max_workers or min(
            threading.active_count() + 4, 16
        )  # More threads for I/O bound tasks
        logger.info(f"ParallelPairDetector initialized with {self.max_workers} threads")

    def find_suspicious_pairs(
        self, df: pd.DataFrame, speed_limit: float
    ) -> pd.DataFrame:
        """Find suspicious pairs using parallel processing"""
        if len(df) < 2:
            logger.warning("DataFrame too small for pair detection")
            return pd.DataFrame()

        start_time = time.time()
        logger.info(
            f"Starting parallel detection on {len(df)} records with {self.max_workers} threads"
        )

        # Create chunks for parallel processing
        chunks = self._create_chunks(df, speed_limit)
        logger.debug(f"Created {len(chunks)} chunks for processing")

        # Process chunks in parallel
        chunk_results = self._process_chunks_parallel(chunks)

        # Combine results and remove duplicates
        all_pairs = self._combine_chunk_results(chunk_results)

        total_time = time.time() - start_time
        logger.info(
            f"Parallel detection completed: {len(all_pairs)} pairs found in {total_time:.2f}s"
        )

        return pd.DataFrame(all_pairs)

    def _create_chunks(
        self, df: pd.DataFrame, speed_limit: float
    ) -> list[DetectionChunk]:
        """Create overlapping chunks for parallel processing"""
        # Calculate optimal chunk size based on data size and worker count
        total_rows = len(df)
        optimal_chunk_size = max(
            50, total_rows // (self.max_workers * 2)
        )  # Ensure minimum chunk size

        chunks = []
        chunk_id = 0

        for start_idx in range(0, total_rows, optimal_chunk_size):
            end_idx = min(
                start_idx + optimal_chunk_size + 1, total_rows
            )  # +1 for overlap

            if start_idx >= total_rows - 1:  # Skip if not enough data for pairs
                break

            chunk_data = df.iloc[start_idx:end_idx].copy()

            chunks.append(
                DetectionChunk(
                    chunk_id=chunk_id,
                    data=chunk_data,
                    speed_limit=speed_limit,
                    overlap_rows=1,
                )
            )

            chunk_id += 1

            # If this chunk covers the end, we're done
            if end_idx >= total_rows:
                break

        logger.debug(f"Created {len(chunks)} chunks, avg size: {optimal_chunk_size}")
        return chunks

    def _process_chunks_parallel(
        self, chunks: list[DetectionChunk]
    ) -> list[ChunkResult]:
        """Process chunks in parallel using threading"""
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all chunks for processing
            future_to_chunk = {
                executor.submit(process_detection_chunk, chunk): chunk
                for chunk in chunks
            }

            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.debug(
                        f"Chunk {result.chunk_id}: {result.pairs_found} pairs in {result.processing_time:.2f}s"
                    )
                except Exception as e:
                    logger.error(f"Chunk {chunk.chunk_id} failed: {str(e)}")
                    # Add empty result to maintain order
                    results.append(ChunkResult(chunk.chunk_id, [], 0.0, 0))

        # Sort results by chunk_id to maintain order
        results.sort(key=lambda x: x.chunk_id)
        return results

    def _combine_chunk_results(
        self, chunk_results: list[ChunkResult]
    ) -> list[dict[str, Any]]:
        """Combine chunk results and remove duplicates from overlaps"""
        all_pairs = []
        seen_pairs = set()

        for result in chunk_results:
            for pair in result.pairs:
                # Create a unique key for each pair to detect duplicates
                pair_key = self._create_pair_key(pair)

                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    all_pairs.append(pair)

        logger.debug(
            f"Combined results: {len(all_pairs)} unique pairs from {len(chunk_results)} chunks"
        )
        return all_pairs

    def _create_pair_key(self, pair: dict[str, Any]) -> str:
        """Create unique key for pair deduplication"""
        # Use timestamps and coordinates to create unique identifier
        return f"{pair['DataFormatada']}_{pair['latitude_1']}_{pair['longitude_1']}_{pair['latitude_2']}_{pair['longitude_2']}"


def process_detection_chunk(chunk: DetectionChunk) -> ChunkResult:
    """
    Process a single detection chunk in a separate thread.
    This function is executed by ThreadPoolExecutor workers.
    """
    start_time = time.time()

    try:
        # Use the existing PairDetector logic for each chunk
        pairs = PairDetector._scan_consecutive_pairs(chunk.data, chunk.speed_limit)

        processing_time = time.time() - start_time

        return ChunkResult(
            chunk_id=chunk.chunk_id,
            pairs=pairs,
            processing_time=processing_time,
            pairs_found=len(pairs),
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error processing chunk {chunk.chunk_id}: {str(e)}")

        return ChunkResult(
            chunk_id=chunk.chunk_id,
            pairs=[],
            processing_time=processing_time,
            pairs_found=0,
        )


class DetectionPerformanceTracker:
    """Track performance metrics for detection operations"""

    def __init__(self):
        self.metrics = {
            "sequential_time": 0.0,
            "parallel_time": 0.0,
            "sequential_pairs": 0,
            "parallel_pairs": 0,
            "speedup_factor": 0.0,
        }

    def benchmark_detection_methods(
        self, df: pd.DataFrame, speed_limit: float
    ) -> dict[str, Any]:
        """Benchmark sequential vs parallel detection"""
        logger.info("Starting detection performance benchmark")

        # Test sequential detection
        start_time = time.time()
        sequential_result = PairDetector.find_suspicious_pairs(df, speed_limit)
        sequential_time = time.time() - start_time

        # Test parallel detection
        parallel_detector = ParallelPairDetector()
        start_time = time.time()
        parallel_result = parallel_detector.find_suspicious_pairs(df, speed_limit)
        parallel_time = time.time() - start_time

        # Calculate speedup
        speedup = sequential_time / parallel_time if parallel_time > 0 else 0

        # Update metrics
        self.metrics.update(
            {
                "sequential_time": sequential_time,
                "parallel_time": parallel_time,
                "sequential_pairs": len(sequential_result),
                "parallel_pairs": len(parallel_result),
                "speedup_factor": speedup,
            }
        )

        logger.info(
            f"Benchmark complete: {speedup:.2f}x speedup ({sequential_time:.2f}s → {parallel_time:.2f}s)"
        )

        return {
            "sequential_result": sequential_result,
            "parallel_result": parallel_result,
            "metrics": self.metrics.copy(),
        }
