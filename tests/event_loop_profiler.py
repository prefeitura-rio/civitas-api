# -*- coding: utf-8 -*-
"""
Event Loop Blocking Detection Script

This script provides specific tools to detect and measure event loop blocking
in the Civitas API, focusing on the identified problematic endpoints.
"""

import asyncio
import time
import statistics
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import aiohttp
import sys
from pathlib import Path

# Add app to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from app import config
    from app.utils import get_bigquery_client, get_plate_details, get_path
    from app.models import User
except ImportError as e:
    print(f"Warning: Could not import app modules: {e}")
    print("This script should be run from the project root or with app in PYTHONPATH")


class EventLoopProfiler:
    """
    Profile event loop performance and detect blocking operations.
    """
    
    def __init__(self):
        self.measurements = []
        self.loop = None
        self.monitoring = False
    
    async def start_monitoring(self, interval: float = 0.1):
        """Start monitoring event loop lag."""
        self.loop = asyncio.get_running_loop()
        self.monitoring = True
        self.measurements = []
        
        while self.monitoring:
            start = time.perf_counter()
            await asyncio.sleep(0)  # Yield control
            end = time.perf_counter()
            lag = end - start
            self.measurements.append(lag)
            await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Stop monitoring and return statistics."""
        self.monitoring = False
        
        if not self.measurements:
            return {"error": "No measurements collected"}
        
        return {
            "avg_lag": statistics.mean(self.measurements),
            "max_lag": max(self.measurements),
            "p95_lag": self._percentile(self.measurements, 95),
            "p99_lag": self._percentile(self.measurements, 99),
            "samples": len(self.measurements),
            "blocking_events": len([m for m in self.measurements if m > 0.1])  # >100ms considered blocking
        }
    
    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]


async def profile_bigquery_operations():
    """
    Profile BigQuery operations to detect blocking.
    """
    print("🔍 Profiling BigQuery operations...")
    
    profiler = EventLoopProfiler()
    
    # Start monitoring in background
    monitor_task = asyncio.create_task(profiler.start_monitoring())
    
    try:
        # Test BigQuery client creation (synchronous operation)
        start_time = time.perf_counter()
        client = get_bigquery_client()
        client_creation_time = time.perf_counter() - start_time
        
        print(f"BigQuery client creation time: {client_creation_time:.3f}s")
        
        # Test a simple query
        start_time = time.perf_counter()
        query = """
        SELECT COUNT(*) as total
        FROM `rj-cetrio.ocr_radar.vw_readings`
        LIMIT 1
        """
        job = client.query(query)
        result = job.result(max_results=1)
        list(result)  # Force iteration
        query_time = time.perf_counter() - start_time
        
        print(f"Simple BigQuery query time: {query_time:.3f}s")
        
    except Exception as e:
        print(f"BigQuery test failed: {e}")
    
    finally:
        profiler.stop_monitoring()
        monitor_task.cancel()
        
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    
    stats = profiler.stop_monitoring()
    print(f"Event loop lag during BigQuery operations:")
    print(f"  - Average lag: {stats.get('avg_lag', 0):.3f}s")
    print(f"  - Max lag: {stats.get('max_lag', 0):.3f}s")
    print(f"  - P95 lag: {stats.get('p95_lag', 0):.3f}s")
    print(f"  - Blocking events: {stats.get('blocking_events', 0)}")
    
    return stats


async def profile_cars_plates_operation():
    """
    Profile the cars/plates operation internals.
    """
    print("🚗 Profiling cars/plates operation...")
    
    test_plates = ["ABC1234", "DEF5678", "GHI9012"]
    profiler = EventLoopProfiler()
    
    # Mock user with CPF (you'll need to adjust this)
    class MockUser:
        def __init__(self):
            self.cpf = "12345678901"  # Test CPF
    
    user = MockUser()
    
    # Start monitoring
    monitor_task = asyncio.create_task(profiler.start_monitoring())
    
    try:
        # Test individual plate lookups
        individual_times = []
        for plate in test_plates:
            start_time = time.perf_counter()
            try:
                # This calls the actual function that hits external APIs
                result = await get_plate_details(plate=plate, cpf=user.cpf, raise_for_errors=False)
                individual_time = time.perf_counter() - start_time
                individual_times.append(individual_time)
                print(f"Plate {plate} lookup time: {individual_time:.3f}s")
                
                # Small delay to see event loop behavior
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Plate {plate} lookup failed: {e}")
        
        # Test batch processing with asyncio.gather (simulate the endpoint)
        start_time = time.perf_counter()
        try:
            batch_results = await asyncio.gather(*[
                get_plate_details(plate=plate, cpf=user.cpf, raise_for_errors=False)
                for plate in test_plates
            ], return_exceptions=True)
            batch_time = time.perf_counter() - start_time
            print(f"Batch processing time: {batch_time:.3f}s")
            print(f"Individual sum time: {sum(individual_times):.3f}s")
            print(f"Batch efficiency: {batch_time / sum(individual_times):.2f}x")
            
        except Exception as e:
            print(f"Batch processing failed: {e}")
    
    finally:
        profiler.stop_monitoring()
        monitor_task.cancel()
        
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    
    stats = profiler.stop_monitoring()
    print(f"Event loop lag during cars/plates operations:")
    print(f"  - Average lag: {stats.get('avg_lag', 0):.3f}s")
    print(f"  - Max lag: {stats.get('max_lag', 0):.3f}s")
    print(f"  - P95 lag: {stats.get('p95_lag', 0):.3f}s")
    print(f"  - Blocking events: {stats.get('blocking_events', 0)}")
    
    return stats


async def profile_cars_path_operation():
    """
    Profile the cars/path operation internals.
    """
    print("🛣️  Profiling cars/path operation...")
    
    test_plate = "ABC1234"
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    
    # Convert to pendulum DateTime (as used in the actual function)
    try:
        from pendulum import DateTime
        start_pendulum = DateTime.instance(start_time)
        end_pendulum = DateTime.instance(end_time)
    except ImportError:
        print("Pendulum not available, using datetime")
        start_pendulum = start_time
        end_pendulum = end_time
    
    profiler = EventLoopProfiler()
    
    # Start monitoring
    monitor_task = asyncio.create_task(profiler.start_monitoring())
    
    try:
        # Test the path operation
        start_operation_time = time.perf_counter()
        try:
            path_result = await get_path(
                placa=test_plate,
                min_datetime=start_pendulum,
                max_datetime=end_pendulum,
                polyline=False
            )
            operation_time = time.perf_counter() - start_operation_time
            print(f"Path operation time: {operation_time:.3f}s")
            print(f"Path segments returned: {len(path_result) if path_result else 0}")
            
        except Exception as e:
            print(f"Path operation failed: {e}")
    
    finally:
        profiler.stop_monitoring()
        monitor_task.cancel()
        
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    
    stats = profiler.stop_monitoring()
    print(f"Event loop lag during cars/path operations:")
    print(f"  - Average lag: {stats.get('avg_lag', 0):.3f}s")
    print(f"  - Max lag: {stats.get('max_lag', 0):.3f}s")
    print(f"  - P95 lag: {stats.get('p95_lag', 0):.3f}s")
    print(f"  - Blocking events: {stats.get('blocking_events', 0)}")
    
    return stats


async def test_concurrent_load():
    """
    Test concurrent load on the actual API endpoints.
    """
    print("🔄 Testing concurrent load on API endpoints...")
    
    base_url = "http://localhost:8000"
    
    async def test_endpoint(session: aiohttp.ClientSession, url: str, method: str = "GET", payload: dict = None):
        """Test a single endpoint call."""
        start_time = time.perf_counter()
        try:
            if method.upper() == "POST":
                async with session.post(url, json=payload) as response:
                    await response.text()
                    return time.perf_counter() - start_time, response.status, None
            else:
                async with session.get(url) as response:
                    await response.text()
                    return time.perf_counter() - start_time, response.status, None
        except Exception as e:
            return time.perf_counter() - start_time, 0, str(e)
    
    # Test configurations
    tests = [
        {
            "name": "cars/plates (batch)",
            "url": f"{base_url}/cars/plates",
            "method": "POST",
            "payload": {
                "plates": ["ABC1234", "DEF5678", "GHI9012"],
                "raise_for_errors": False
            },
            "concurrent": 5
        },
        {
            "name": "cars/path",
            "url": f"{base_url}/cars/path?placa=ABC1234&start_time={datetime.now() - timedelta(hours=1)}&end_time={datetime.now()}&polyline=false",
            "method": "GET",
            "payload": None,
            "concurrent": 3
        }
    ]
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        for test_config in tests:
            print(f"\n📊 Testing {test_config['name']}...")
            
            # Create concurrent tasks
            tasks = []
            for i in range(test_config["concurrent"]):
                task = test_endpoint(
                    session=session,
                    url=test_config["url"],
                    method=test_config["method"],
                    payload=test_config["payload"]
                )
                tasks.append(task)
            
            # Execute concurrently
            start_time = time.perf_counter()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.perf_counter() - start_time
            
            # Analyze results
            response_times = []
            errors = []
            success_count = 0
            
            for result in results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                elif isinstance(result, tuple):
                    response_time, status, error = result
                    response_times.append(response_time)
                    if error:
                        errors.append(error)
                    elif 200 <= status < 300:
                        success_count += 1
            
            print(f"Results for {test_config['name']}:")
            print(f"  - Total time: {total_time:.2f}s")
            print(f"  - Successful requests: {success_count}/{test_config['concurrent']}")
            print(f"  - Errors: {len(errors)}")
            if response_times:
                print(f"  - Avg response time: {statistics.mean(response_times):.2f}s")
                print(f"  - Max response time: {max(response_times):.2f}s")
            if errors:
                print(f"  - Error examples: {errors[:3]}")


async def main():
    """
    Main function to run all profiling tests.
    """
    print("🚀 Starting Event Loop Blocking Analysis for Civitas API")
    print("=" * 60)
    
    try:
        # Test 1: BigQuery operations
        await profile_bigquery_operations()
        print("\n" + "=" * 60)
        
        # Test 2: Cars/plates operations
        await profile_cars_plates_operation()
        print("\n" + "=" * 60)
        
        # Test 3: Cars/path operations
        await profile_cars_path_operation()
        print("\n" + "=" * 60)
        
        # Test 4: Concurrent API load
        await test_concurrent_load()
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("✅ Event loop blocking analysis complete!")


if __name__ == "__main__":
    asyncio.run(main())
