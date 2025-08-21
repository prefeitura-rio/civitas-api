# -*- coding: utf-8 -*-
"""
Quick Event Loop Test Script

Simple script to test specific blocking operations in the Civitas API.
Run this script while the API is running to identify event loop blocking.
"""

import asyncio
import time
import json
from datetime import datetime, timedelta


async def measure_event_loop_lag():
    """
    Measure event loop lag to detect blocking operations.
    """
    measurements = []
    
    for _ in range(100):  # Take 100 measurements
        start = time.perf_counter()
        await asyncio.sleep(0)  # Yield control to event loop
        end = time.perf_counter()
        lag = end - start
        measurements.append(lag)
        await asyncio.sleep(0.01)  # 10ms interval
    
    avg_lag = sum(measurements) / len(measurements)
    max_lag = max(measurements)
    blocking_events = len([m for m in measurements if m > 0.1])  # >100ms
    
    return {
        "avg_lag_ms": avg_lag * 1000,
        "max_lag_ms": max_lag * 1000,
        "blocking_events": blocking_events,
        "total_measurements": len(measurements)
    }


async def simulate_bigquery_blocking():
    """
    Simulate the BigQuery blocking behavior we identified.
    """
    print("🔍 Simulating BigQuery operations...")
    
    # Simulate synchronous BigQuery client creation and query
    # (This mimics the blocking behavior in get_bigquery_client())
    
    def blocking_operation(duration=0.5):
        """Simulate a blocking operation like BigQuery."""
        time.sleep(duration)  # This blocks the event loop!
        return f"Completed after {duration}s"
    
    # Measure event loop lag while doing blocking operation
    lag_task = asyncio.create_task(measure_event_loop_lag())
    
    # Simulate the problematic pattern from utils.py
    start_time = time.perf_counter()
    
    # This is what happens in get_bigquery_client() - blocking!
    result = blocking_operation(0.3)
    
    operation_time = time.perf_counter() - start_time
    
    # Wait for lag measurements to complete
    lag_stats = await lag_task
    
    print(f"Blocking operation took: {operation_time:.3f}s")
    print(f"Event loop lag during operation:")
    print(f"  - Average lag: {lag_stats['avg_lag_ms']:.1f}ms")
    print(f"  - Max lag: {lag_stats['max_lag_ms']:.1f}ms")
    print(f"  - Blocking events: {lag_stats['blocking_events']}")
    
    return lag_stats


async def simulate_batch_processing():
    """
    Simulate the batch processing behavior from /cars/plates.
    """
    print("🚗 Simulating cars/plates batch processing...")
    
    async def mock_api_call(plate, delay=0.2):
        """Mock external API call (like Cortex API)."""
        await asyncio.sleep(delay)  # Simulate network I/O
        return {"plate": plate, "data": f"info_for_{plate}"}
    
    # Test different batch sizes
    batch_sizes = [1, 5, 10, 20]
    
    for batch_size in batch_sizes:
        plates = [f"ABC{i:04d}" for i in range(batch_size)]
        
        # Measure event loop lag during batch processing
        lag_task = asyncio.create_task(measure_event_loop_lag())
        
        # Simulate the asyncio.gather() pattern from the endpoint
        start_time = time.perf_counter()
        
        results = await asyncio.gather(*[
            mock_api_call(plate) for plate in plates
        ])
        
        batch_time = time.perf_counter() - start_time
        
        # Get lag measurements
        lag_stats = await lag_task
        
        print(f"Batch size {batch_size}:")
        print(f"  - Total time: {batch_time:.2f}s")
        print(f"  - Avg time per plate: {batch_time/batch_size:.2f}s")
        print(f"  - Event loop lag: {lag_stats['avg_lag_ms']:.1f}ms avg, {lag_stats['max_lag_ms']:.1f}ms max")
        print(f"  - Blocking events: {lag_stats['blocking_events']}")
        print()


async def simulate_pdf_generation():
    """
    Simulate the PDF generation blocking behavior.
    """
    print("📄 Simulating PDF generation...")
    
    def blocking_pdf_generation(duration=2.0):
        """Simulate CPU-intensive PDF generation."""
        # This simulates WeasyPrint or FPDF operations
        start = time.perf_counter()
        while time.perf_counter() - start < duration:
            # Simulate CPU work
            _ = sum(i * i for i in range(10000))
        return "PDF generated"
    
    # Measure event loop lag during PDF generation
    lag_task = asyncio.create_task(measure_event_loop_lag())
    
    start_time = time.perf_counter()
    
    # This blocks the event loop - similar to PDF generation
    result = blocking_pdf_generation(1.0)
    
    generation_time = time.perf_counter() - start_time
    
    # Get lag measurements
    lag_stats = await lag_task
    
    print(f"PDF generation took: {generation_time:.3f}s")
    print(f"Event loop lag during generation:")
    print(f"  - Average lag: {lag_stats['avg_lag_ms']:.1f}ms")
    print(f"  - Max lag: {lag_stats['max_lag_ms']:.1f}ms")
    print(f"  - Blocking events: {lag_stats['blocking_events']}")
    
    return lag_stats


async def test_concurrent_vs_sequential():
    """
    Test the difference between concurrent and sequential processing.
    """
    print("⚡ Testing concurrent vs sequential processing...")
    
    async def api_call(delay=0.3):
        """Simulate an API call."""
        await asyncio.sleep(delay)
        return "result"
    
    num_calls = 10
    
    # Sequential processing
    print("Sequential processing:")
    lag_task_seq = asyncio.create_task(measure_event_loop_lag())
    
    start_time = time.perf_counter()
    sequential_results = []
    for _ in range(num_calls):
        result = await api_call()
        sequential_results.append(result)
    sequential_time = time.perf_counter() - start_time
    
    lag_stats_seq = await lag_task_seq
    
    # Concurrent processing
    print("Concurrent processing:")
    lag_task_conc = asyncio.create_task(measure_event_loop_lag())
    
    start_time = time.perf_counter()
    concurrent_results = await asyncio.gather(*[
        api_call() for _ in range(num_calls)
    ])
    concurrent_time = time.perf_counter() - start_time
    
    lag_stats_conc = await lag_task_conc
    
    print(f"Sequential: {sequential_time:.2f}s, lag: {lag_stats_seq['avg_lag_ms']:.1f}ms avg")
    print(f"Concurrent: {concurrent_time:.2f}s, lag: {lag_stats_conc['avg_lag_ms']:.1f}ms avg")
    print(f"Speedup: {sequential_time/concurrent_time:.1f}x")


async def main():
    """
    Run all event loop blocking tests.
    """
    print("🚀 Event Loop Blocking Analysis")
    print("=" * 50)
    
    # Test 1: Baseline event loop performance
    print("📊 Measuring baseline event loop performance...")
    baseline = await measure_event_loop_lag()
    print(f"Baseline event loop lag: {baseline['avg_lag_ms']:.1f}ms avg, {baseline['max_lag_ms']:.1f}ms max")
    print()
    
    # Test 2: Simulate BigQuery blocking
    await simulate_bigquery_blocking()
    print()
    
    # Test 3: Simulate batch processing
    await simulate_batch_processing()
    print()
    
    # Test 4: Simulate PDF generation
    await simulate_pdf_generation()
    print()
    
    # Test 5: Concurrent vs sequential
    await test_concurrent_vs_sequential()
    print()
    
    print("✅ Analysis complete!")
    print("\n🔍 Key Findings:")
    print("1. Check if any test shows >100ms average lag")
    print("2. Look for blocking events in concurrent operations")
    print("3. Compare concurrent vs sequential performance")
    print("4. Identify which operations cause the most blocking")


if __name__ == "__main__":
    asyncio.run(main())
