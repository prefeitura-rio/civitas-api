# -*- coding: utf-8 -*-
"""
Performance tests for event loop blocking analysis.

These tests are designed to identify potential event loop blocking issues
in the Civitas API, specifically focusing on the most resource-intensive endpoints.
"""

import asyncio
import time
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pytest
import httpx
from loguru import logger

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30.0
CONCURRENT_REQUESTS = [1, 5, 10, 20]  # Different concurrency levels to test


class EventLoopMonitor:
    """Monitor event loop performance during tests."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.response_times = []
        self.errors = []
    
    def start(self):
        """Start monitoring."""
        self.start_time = time.perf_counter()
        self.response_times = []
        self.errors = []
    
    def record_response(self, response_time: float, error: str = None):
        """Record a response time and optional error."""
        self.response_times.append(response_time)
        if error:
            self.errors.append(error)
    
    def stop(self):
        """Stop monitoring and return stats."""
        self.end_time = time.perf_counter()
        total_time = self.end_time - self.start_time
        
        if not self.response_times:
            return {
                "total_time": total_time,
                "requests": 0,
                "errors": len(self.errors),
                "error_rate": 1.0 if self.errors else 0.0
            }
        
        return {
            "total_time": total_time,
            "requests": len(self.response_times),
            "avg_response_time": statistics.mean(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times),
            "p95_response_time": self._percentile(self.response_times, 95),
            "p99_response_time": self._percentile(self.response_times, 99),
            "errors": len(self.errors),
            "error_rate": len(self.errors) / len(self.response_times),
            "requests_per_second": len(self.response_times) / total_time if total_time > 0 else 0
        }
    
    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile of response times."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]


async def make_authenticated_request(
    client: httpx.AsyncClient,
    method: str,
    endpoint: str,
    **kwargs
) -> tuple[float, httpx.Response, str]:
    """
    Make an authenticated request and measure response time.
    
    Returns:
        tuple: (response_time, response, error_message)
    """
    start_time = time.perf_counter()
    error_message = None
    
    try:
        # TODO: Replace with actual authentication token
        headers = kwargs.get("headers", {})
        headers.update({
            "Authorization": "Bearer your_test_token_here",
            "Content-Type": "application/json"
        })
        kwargs["headers"] = headers
        
        response = await client.request(method, f"{BASE_URL}{endpoint}", **kwargs)
        response.raise_for_status()
        
    except httpx.TimeoutException:
        error_message = "Request timeout"
        response = None
    except httpx.HTTPStatusError as e:
        error_message = f"HTTP {e.response.status_code}: {e.response.text}"
        response = e.response
    except Exception as e:
        error_message = f"Request failed: {str(e)}"
        response = None
    
    end_time = time.perf_counter()
    response_time = end_time - start_time
    
    return response_time, response, error_message


async def concurrent_requests(
    endpoint: str,
    method: str = "GET",
    payload: Dict[str, Any] = None,
    concurrency: int = 10,
    total_requests: int = 100
) -> Dict[str, Any]:
    """
    Execute concurrent requests to test event loop blocking.
    
    Args:
        endpoint: API endpoint to test
        method: HTTP method
        payload: Request payload for POST requests
        concurrency: Number of concurrent requests
        total_requests: Total number of requests to make
    
    Returns:
        Performance statistics
    """
    monitor = EventLoopMonitor()
    monitor.start()
    
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def make_request():
            async with semaphore:
                kwargs = {}
                if payload and method.upper() == "POST":
                    kwargs["json"] = payload
                
                response_time, response, error = await make_authenticated_request(
                    client, method, endpoint, **kwargs
                )
                monitor.record_response(response_time, error)
                return response_time, response, error
        
        # Execute all requests
        tasks = [make_request() for _ in range(total_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        monitor.errors.extend([str(e) for e in exceptions])
    
    stats = monitor.stop()
    stats["concurrency"] = concurrency
    stats["total_requests"] = total_requests
    
    return stats


class TestCarsPlatesPerformance:
    """Test performance of /cars/plates endpoint."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("concurrency", CONCURRENT_REQUESTS)
    async def test_cars_plates_concurrency(self, concurrency):
        """
        Test /cars/plates endpoint under different concurrency levels.
        
        This test focuses on:
        - Event loop blocking during batch processing
        - Response time degradation with increased load
        - Error rates under stress
        """
        # Test payload with multiple plates
        test_plates = [
            "ABC1234", "DEF5678", "GHI9012", "JKL3456", "MNO7890",
            "PQR1357", "STU2468", "VWX9753", "YZA1111", "BCD2222"
        ]
        
        payload = {
            "plates": test_plates,
            "raise_for_errors": False
        }
        
        logger.info(f"Testing /cars/plates with concurrency: {concurrency}")
        
        stats = await concurrent_requests(
            endpoint="/cars/plates",
            method="POST",
            payload=payload,
            concurrency=concurrency,
            total_requests=20  # Fewer requests for this heavy endpoint
        )
        
        # Log results
        logger.info(f"Results for concurrency {concurrency}:")
        logger.info(f"  - Avg response time: {stats['avg_response_time']:.2f}s")
        logger.info(f"  - P95 response time: {stats['p95_response_time']:.2f}s")
        logger.info(f"  - Error rate: {stats['error_rate']:.2%}")
        logger.info(f"  - Requests per second: {stats['requests_per_second']:.2f}")
        
        # Assertions to catch performance degradation
        assert stats["error_rate"] < 0.1, f"Error rate too high: {stats['error_rate']:.2%}"
        assert stats["avg_response_time"] < 10.0, f"Average response time too slow: {stats['avg_response_time']:.2f}s"
        
        # Check for event loop blocking (P99 should not be orders of magnitude higher than median)
        if stats["requests"] > 5:  # Only check if we have enough data
            ratio = stats["p99_response_time"] / stats["median_response_time"]
            assert ratio < 10.0, f"P99/median ratio too high ({ratio:.2f}), suggesting event loop blocking"
    
    @pytest.mark.asyncio
    async def test_cars_plates_single_vs_batch(self):
        """
        Compare single plate requests vs batch requests to identify batching overhead.
        """
        test_plate = "ABC1234"
        
        # Test single plate request
        single_payload = {
            "plates": [test_plate],
            "raise_for_errors": False
        }
        
        logger.info("Testing single plate request...")
        single_stats = await concurrent_requests(
            endpoint="/cars/plates",
            method="POST",
            payload=single_payload,
            concurrency=1,
            total_requests=10
        )
        
        # Test batch request
        batch_payload = {
            "plates": [f"ABC{i:04d}" for i in range(10)],  # 10 plates
            "raise_for_errors": False
        }
        
        logger.info("Testing batch plate request...")
        batch_stats = await concurrent_requests(
            endpoint="/cars/plates",
            method="POST",
            payload=batch_payload,
            concurrency=1,
            total_requests=5
        )
        
        logger.info(f"Single plate avg response time: {single_stats['avg_response_time']:.2f}s")
        logger.info(f"Batch (10 plates) avg response time: {batch_stats['avg_response_time']:.2f}s")
        
        # Batch should be more efficient than 10 individual requests
        efficiency_ratio = batch_stats['avg_response_time'] / (single_stats['avg_response_time'] * 10)
        logger.info(f"Batch efficiency ratio: {efficiency_ratio:.2f}")
        
        assert efficiency_ratio < 0.8, "Batch processing should be more efficient than individual requests"


class TestCarsPathPerformance:
    """Test performance of /cars/path endpoint."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("concurrency", CONCURRENT_REQUESTS)
    async def test_cars_path_concurrency(self, concurrency):
        """
        Test /cars/path endpoint under different concurrency levels.
        
        This test focuses on:
        - BigQuery query performance under load
        - Google Maps API integration blocking
        - Memory usage during path processing
        """
        # Test parameters
        test_plate = "ABC1234"
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)  # 1 hour window
        
        endpoint = f"/cars/path?placa={test_plate}&start_time={start_time.isoformat()}&end_time={end_time.isoformat()}&polyline=false"
        
        logger.info(f"Testing /cars/path with concurrency: {concurrency}")
        
        stats = await concurrent_requests(
            endpoint=endpoint,
            method="GET",
            concurrency=concurrency,
            total_requests=15  # Fewer requests for this heavy endpoint
        )
        
        # Log results
        logger.info(f"Results for concurrency {concurrency}:")
        logger.info(f"  - Avg response time: {stats['avg_response_time']:.2f}s")
        logger.info(f"  - P95 response time: {stats['p95_response_time']:.2f}s")
        logger.info(f"  - Error rate: {stats['error_rate']:.2%}")
        logger.info(f"  - Requests per second: {stats['requests_per_second']:.2f}")
        
        # Assertions for BigQuery-heavy endpoint
        assert stats["error_rate"] < 0.15, f"Error rate too high: {stats['error_rate']:.2%}"
        assert stats["avg_response_time"] < 15.0, f"Average response time too slow: {stats['avg_response_time']:.2f}s"
        
        # Check for severe event loop blocking
        if stats["requests"] > 5:
            ratio = stats["p95_response_time"] / stats["median_response_time"]
            assert ratio < 5.0, f"P95/median ratio too high ({ratio:.2f}), suggesting BigQuery blocking"
    
    @pytest.mark.asyncio
    async def test_cars_path_time_window_impact(self):
        """
        Test how different time windows affect performance.
        """
        test_plate = "ABC1234"
        end_time = datetime.now()
        
        time_windows = [
            ("1 hour", timedelta(hours=1)),
            ("6 hours", timedelta(hours=6)),
            ("24 hours", timedelta(hours=24)),
        ]
        
        results = {}
        
        for window_name, window_delta in time_windows:
            start_time = end_time - window_delta
            endpoint = f"/cars/path?placa={test_plate}&start_time={start_time.isoformat()}&end_time={end_time.isoformat()}&polyline=false"
            
            logger.info(f"Testing {window_name} time window...")
            
            stats = await concurrent_requests(
                endpoint=endpoint,
                method="GET",
                concurrency=2,
                total_requests=5
            )
            
            results[window_name] = stats
            logger.info(f"{window_name} - Avg response time: {stats['avg_response_time']:.2f}s")
        
        # Verify that larger time windows don't cause exponential performance degradation
        hour_1_time = results["1 hour"]["avg_response_time"]
        hour_24_time = results["24 hours"]["avg_response_time"]
        
        # 24-hour window should not be more than 10x slower than 1-hour window
        ratio = hour_24_time / hour_1_time if hour_1_time > 0 else float('inf')
        logger.info(f"24h/1h performance ratio: {ratio:.2f}")
        
        assert ratio < 10.0, f"24-hour window is {ratio:.2f}x slower than 1-hour, suggesting poor query optimization"
    
    @pytest.mark.asyncio
    async def test_cars_path_polyline_overhead(self):
        """
        Test the performance impact of polyline generation.
        """
        test_plate = "ABC1234"
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=2)
        
        # Test without polyline
        endpoint_no_polyline = f"/cars/path?placa={test_plate}&start_time={start_time.isoformat()}&end_time={end_time.isoformat()}&polyline=false"
        
        logger.info("Testing without polyline...")
        no_polyline_stats = await concurrent_requests(
            endpoint=endpoint_no_polyline,
            method="GET",
            concurrency=2,
            total_requests=5
        )
        
        # Test with polyline
        endpoint_with_polyline = f"/cars/path?placa={test_plate}&start_time={start_time.isoformat()}&end_time={end_time.isoformat()}&polyline=true"
        
        logger.info("Testing with polyline...")
        with_polyline_stats = await concurrent_requests(
            endpoint=endpoint_with_polyline,
            method="GET",
            concurrency=2,
            total_requests=5
        )
        
        no_polyline_time = no_polyline_stats["avg_response_time"]
        with_polyline_time = with_polyline_stats["avg_response_time"]
        
        logger.info(f"Without polyline avg response time: {no_polyline_time:.2f}s")
        logger.info(f"With polyline avg response time: {with_polyline_time:.2f}s")
        
        # Polyline generation should add overhead but not be excessive
        overhead_ratio = with_polyline_time / no_polyline_time if no_polyline_time > 0 else float('inf')
        logger.info(f"Polyline overhead ratio: {overhead_ratio:.2f}")
        
        assert overhead_ratio < 3.0, f"Polyline generation adds {overhead_ratio:.2f}x overhead, too much"


if __name__ == "__main__":
    """
    Run tests manually for debugging.
    """
    import asyncio
    
    async def main():
        # Test cars/plates
        test_plates = TestCarsPlatesPerformance()
        await test_plates.test_cars_plates_concurrency(5)
        await test_plates.test_cars_plates_single_vs_batch()
        
        # Test cars/path
        test_path = TestCarsPathPerformance()
        await test_path.test_cars_path_concurrency(5)
        await test_path.test_cars_path_time_window_impact()
        await test_path.test_cars_path_polyline_overhead()
    
    asyncio.run(main())
