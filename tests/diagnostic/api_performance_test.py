#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Endpoint Performance Tester

This script tests the actual /cars/plates and /cars/path endpoints
to identify event loop blocking issues under different load conditions.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode
import subprocess
import sys


async def make_http_request(url, method="GET", data=None, headers=None):
    """
    Make HTTP request using curl (no external dependencies needed).
    """
    cmd = ["curl", "-s", "-w", "%{http_code},%{time_total}"]
    
    if headers:
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
    
    if method.upper() == "POST":
        cmd.extend(["-X", "POST"])
        if data:
            cmd.extend(["-H", "Content-Type: application/json"])
            cmd.extend(["-d", json.dumps(data)])
    
    cmd.append(url)
    
    try:
        start_time = time.perf_counter()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        end_time = time.perf_counter()
        
        if result.returncode != 0:
            return None, 0, f"curl failed: {result.stderr}"
        
        # Parse curl output
        output_lines = result.stdout.strip().split('\n')
        if len(output_lines) < 1:
            return None, 0, "No output from curl"
        
        # Last line contains status code and time
        last_line = output_lines[-1]
        if ',' in last_line:
            status_code, curl_time = last_line.split(',')
            try:
                status_code = int(status_code)
                curl_time = float(curl_time)
            except ValueError:
                status_code = 0
                curl_time = end_time - start_time
        else:
            status_code = 0
            curl_time = end_time - start_time
        
        # Response body is everything except the last line
        response_body = '\n'.join(output_lines[:-1]) if len(output_lines) > 1 else ""
        
        return response_body, status_code, None
        
    except subprocess.TimeoutExpired:
        return None, 0, "Request timeout"
    except Exception as e:
        return None, 0, f"Request failed: {str(e)}"


async def test_cars_plates_endpoint():
    """
    Test the /cars/plates endpoint with different batch sizes.
    """
    print("🚗 Testing /cars/plates endpoint...")
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/cars/plates"
    
    # Test different batch sizes
    batch_tests = [
        {"name": "Single plate", "plates": ["ABC1234"]},
        {"name": "Small batch (3)", "plates": ["ABC1234", "DEF5678", "GHI9012"]},
        {"name": "Medium batch (5)", "plates": [f"ABC{i:04d}" for i in range(5)]},
        {"name": "Large batch (10)", "plates": [f"ABC{i:04d}" for i in range(10)]},
    ]
    
    # TODO: Replace with actual auth token
    headers = {
        "Authorization": "Bearer your_token_here",
        "Content-Type": "application/json"
    }
    
    for test in batch_tests:
        print(f"\n📊 Testing {test['name']}...")
        
        payload = {
            "plates": test["plates"],
            "raise_for_errors": False
        }
        
        # Test sequential requests
        sequential_times = []
        for i in range(3):  # 3 sequential requests
            start_time = time.perf_counter()
            response, status, error = await make_http_request(endpoint, "POST", payload, headers)
            request_time = time.perf_counter() - start_time
            
            if error:
                print(f"  Request {i+1} failed: {error}")
            elif status == 401:
                print(f"  Request {i+1}: Authentication required (401)")
            elif 200 <= status < 300:
                sequential_times.append(request_time)
                print(f"  Request {i+1}: {request_time:.2f}s (Status: {status})")
            else:
                print(f"  Request {i+1}: Failed with status {status}")
        
        if sequential_times:
            avg_time = sum(sequential_times) / len(sequential_times)
            print(f"  Average time: {avg_time:.2f}s")
        
        # Test concurrent requests
        print(f"  Testing concurrent requests...")
        
        async def single_request():
            start_time = time.perf_counter()
            response, status, error = await make_http_request(endpoint, "POST", payload, headers)
            return time.perf_counter() - start_time, status, error
        
        # Run 3 concurrent requests
        concurrent_start = time.perf_counter()
        concurrent_results = await asyncio.gather(*[single_request() for _ in range(3)])
        total_concurrent_time = time.perf_counter() - concurrent_start
        
        concurrent_times = []
        for i, (req_time, status, error) in enumerate(concurrent_results):
            if error:
                print(f"  Concurrent request {i+1} failed: {error}")
            elif status == 401:
                print(f"  Concurrent request {i+1}: Auth required (401)")
            elif 200 <= status < 300:
                concurrent_times.append(req_time)
                print(f"  Concurrent request {i+1}: {req_time:.2f}s")
        
        if concurrent_times:
            avg_concurrent = sum(concurrent_times) / len(concurrent_times)
            print(f"  Concurrent average: {avg_concurrent:.2f}s")
            print(f"  Total concurrent time: {total_concurrent_time:.2f}s")
            
            if sequential_times:
                efficiency = total_concurrent_time / (avg_time * 3)
                print(f"  Concurrency efficiency: {efficiency:.2f} (lower is better)")


async def test_cars_path_endpoint():
    """
    Test the /cars/path endpoint with different time ranges.
    """
    print("\n🛣️  Testing /cars/path endpoint...")
    
    base_url = "http://localhost:8000"
    test_plate = "ABC1234"
    
    # Test different time ranges
    end_time = datetime.now()
    time_ranges = [
        {"name": "1 hour", "start": end_time - timedelta(hours=1)},
        {"name": "6 hours", "start": end_time - timedelta(hours=6)},
        {"name": "24 hours", "start": end_time - timedelta(hours=24)},
    ]
    
    headers = {
        "Authorization": "Bearer your_token_here"
    }
    
    for test_range in time_ranges:
        print(f"\n📊 Testing {test_range['name']} range...")
        
        params = {
            "placa": test_plate,
            "start_time": test_range["start"].isoformat(),
            "end_time": end_time.isoformat(),
            "polyline": "false"
        }
        
        endpoint = f"{base_url}/cars/path?{urlencode(params)}"
        
        # Test without polyline
        start_time = time.perf_counter()
        response, status, error = await make_http_request(endpoint, "GET", headers=headers)
        request_time = time.perf_counter() - start_time
        
        if error:
            print(f"  Request failed: {error}")
        elif status == 401:
            print(f"  Authentication required (401)")
        elif 200 <= status < 300:
            print(f"  Time: {request_time:.2f}s (Status: {status})")
            # Try to parse response size
            if response:
                try:
                    data = json.loads(response)
                    if isinstance(data, list):
                        print(f"  Path segments: {len(data)}")
                except:
                    print(f"  Response size: {len(response)} bytes")
        else:
            print(f"  Failed with status {status}")
        
        # Test with polyline
        params["polyline"] = "true"
        endpoint_polyline = f"{base_url}/cars/path?{urlencode(params)}"
        
        start_time = time.perf_counter()
        response, status, error = await make_http_request(endpoint_polyline, "GET", headers=headers)
        polyline_time = time.perf_counter() - start_time
        
        if error:
            print(f"  Polyline request failed: {error}")
        elif status == 401:
            print(f"  Polyline: Authentication required (401)")
        elif 200 <= status < 300:
            print(f"  Polyline time: {polyline_time:.2f}s")
            if request_time > 0:
                overhead = polyline_time / request_time
                print(f"  Polyline overhead: {overhead:.1f}x")
        else:
            print(f"  Polyline failed with status {status}")


async def test_concurrent_mixed_load():
    """
    Test mixed concurrent load on both endpoints.
    """
    print("\n⚡ Testing mixed concurrent load...")
    
    base_url = "http://localhost:8000"
    headers = {"Authorization": "Bearer your_token_here"}
    
    # Define mixed workload
    tasks = []
    
    # Add cars/plates tasks
    for i in range(3):
        payload = {
            "plates": [f"TST{i:04d}", f"TST{i+100:04d}"],
            "raise_for_errors": False
        }
        task = make_http_request(f"{base_url}/cars/plates", "POST", payload, headers)
        tasks.append(("plates", task))
    
    # Add cars/path tasks
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=2)
    
    for i in range(2):
        params = {
            "placa": f"TST{i:04d}",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "polyline": "false"
        }
        endpoint = f"{base_url}/cars/path?{urlencode(params)}"
        task = make_http_request(endpoint, "GET", headers=headers)
        tasks.append(("path", task))
    
    print(f"Running {len(tasks)} concurrent requests...")
    
    start_time = time.perf_counter()
    results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
    total_time = time.perf_counter() - start_time
    
    print(f"Total time for {len(tasks)} concurrent requests: {total_time:.2f}s")
    
    # Analyze results by type
    plates_times = []
    path_times = []
    
    for i, (task_type, result) in enumerate(zip([t[0] for t in tasks], results)):
        if isinstance(result, Exception):
            print(f"  {task_type} task {i+1}: Exception - {result}")
        else:
            response, status, error = result
            if error:
                print(f"  {task_type} task {i+1}: Error - {error}")
            elif status == 401:
                print(f"  {task_type} task {i+1}: Auth required")
            elif 200 <= status < 300:
                print(f"  {task_type} task {i+1}: Success (Status: {status})")
            else:
                print(f"  {task_type} task {i+1}: Status {status}")


async def check_api_health():
    """
    Check if the API is running and accessible.
    """
    print("🔍 Checking API health...")
    
    base_url = "http://localhost:8000"
    health_endpoint = f"{base_url}/health"
    
    response, status, error = await make_http_request(health_endpoint, "GET")
    
    if error:
        print(f"❌ API health check failed: {error}")
        return False
    elif status == 200:
        print(f"✅ API is running (Status: {status})")
        return True
    else:
        print(f"⚠️  API responded with status {status}")
        return False


async def main():
    """
    Main function to run all endpoint tests.
    """
    print("🚀 Civitas API Performance Testing")
    print("=" * 50)
    
    # Check if API is running
    api_running = await check_api_health()
    
    if not api_running:
        print("\n❌ API is not accessible. Please ensure:")
        print("1. The API is running on localhost:8000")
        print("2. You have proper authentication configured")
        print("3. Run: poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return
    
    print("\n" + "=" * 50)
    
    # Test individual endpoints
    await test_cars_plates_endpoint()
    await test_cars_path_endpoint()
    
    # Test mixed concurrent load
    await test_concurrent_mixed_load()
    
    print("\n" + "=" * 50)
    print("✅ Performance testing complete!")
    print("\n🔍 Things to look for:")
    print("1. High response times (>5s for plates, >10s for path)")
    print("2. Poor concurrency efficiency (>1.0)")
    print("3. High polyline overhead (>3x)")
    print("4. Authentication errors (need valid token)")


if __name__ == "__main__":
    asyncio.run(main())
