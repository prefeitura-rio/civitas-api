#!/usr/bin/env python3
"""
Simple load test to demonstrate event loop blocking
"""

import asyncio
import aiohttp
import time
from datetime import datetime

async def make_request(session, url, method="GET", json_data=None):
    """Make a single HTTP request."""
    start_time = time.perf_counter()
    try:
        if method.upper() == "POST":
            async with session.post(url, json=json_data) as response:
                await response.text()
                return time.perf_counter() - start_time, response.status, None
        else:
            async with session.get(url) as response:
                await response.text()
                return time.perf_counter() - start_time, response.status, None
    except Exception as e:
        return time.perf_counter() - start_time, 0, str(e)

async def test_concurrent_requests():
    """Test concurrent requests to demonstrate blocking."""
    base_url = "http://localhost:8000"
    
    # Different test scenarios
    scenarios = [
        {
            "name": "Small batch (non-blocking)",
            "url": f"{base_url}/test/cars/plates",
            "method": "POST",
            "payload": {"plates": ["ABC1234", "DEF5678"]},
            "concurrent": 5
        },
        {
            "name": "Large batch (blocking)",
            "url": f"{base_url}/test/cars/plates", 
            "method": "POST",
            "payload": {"plates": [f"ABC{i:04d}" for i in range(8)]},  # 8 plates = blocking pattern
            "concurrent": 3
        },
        {
            "name": "Path query (1h)",
            "url": f"{base_url}/test/cars/path?placa=ABC1234&hours=1",
            "method": "GET",
            "payload": None,
            "concurrent": 4
        },
        {
            "name": "Path query (10h - heavy blocking)",
            "url": f"{base_url}/test/cars/path?placa=ABC1234&hours=10",
            "method": "GET", 
            "payload": None,
            "concurrent": 2
        }
    ]
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        for scenario in scenarios:
            print(f"\n🧪 Testing: {scenario['name']}")
            print(f"   Concurrent requests: {scenario['concurrent']}")
            
            # Create tasks
            tasks = []
            for i in range(scenario["concurrent"]):
                task = make_request(
                    session=session,
                    url=scenario["url"],
                    method=scenario["method"],
                    json_data=scenario["payload"]
                )
                tasks.append(task)
            
            # Execute concurrently and measure
            start_time = time.perf_counter()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.perf_counter() - start_time
            
            # Analyze results
            times = []
            errors = 0
            successes = 0
            
            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                    print(f"   Exception: {result}")
                elif isinstance(result, tuple):
                    req_time, status, error = result
                    times.append(req_time)
                    if error:
                        errors += 1
                        print(f"   Error: {error}")
                    elif 200 <= status < 300:
                        successes += 1
                    else:
                        errors += 1
                        print(f"   HTTP {status}")
            
            print(f"   📊 Results:")
            print(f"     - Total time: {total_time:.2f}s")
            print(f"     - Successful: {successes}/{len(tasks)}")
            print(f"     - Errors: {errors}")
            
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)
                
                print(f"     - Avg response time: {avg_time:.2f}s")
                print(f"     - Min response time: {min_time:.2f}s") 
                print(f"     - Max response time: {max_time:.2f}s")
                
                # Calculate efficiency
                expected_sequential = avg_time * len(tasks)
                efficiency = total_time / expected_sequential if expected_sequential > 0 else 0
                print(f"     - Concurrency efficiency: {efficiency:.2f} (lower is better)")
                
                # Detect potential blocking
                if max_time > avg_time * 3:
                    print(f"     ⚠️  High variance detected - possible event loop blocking!")
                
                if efficiency > 0.8:
                    print(f"     ⚠️  Poor concurrency efficiency - possible blocking!")
            
            await asyncio.sleep(1)  # Brief pause between tests

async def main():
    """Main test function."""
    print("🚀 Event Loop Blocking Demonstration")
    print("=" * 50)
    
    # Check if API is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health") as response:
                if response.status == 200:
                    print("✅ API is running")
                else:
                    print(f"❌ API returned status {response.status}")
                    return
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("   Make sure the test API is running:")
        print("   python tests/test_api.py")
        return
    
    await test_concurrent_requests()
    
    print("\n" + "=" * 50)
    print("✅ Load testing complete!")
    print("\n🔍 Key observations:")
    print("1. Small batches should have good concurrency efficiency (<0.5)")
    print("2. Large batches may show blocking (efficiency >0.8)")
    print("3. Heavy queries (10h) should show clear blocking patterns")
    print("4. High variance in response times indicates event loop blocking")

async def test_real_api():
    """Test real Civitas API endpoints"""
    print("🔍 Testing Real Civitas API")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test /cars/plates endpoint
    print("\n📍 Testing /cars/plates endpoint...")
    plates_payload = {"plates": ["ABC1234", "XYZ5678", "DEF9012"]}
    
    start_time = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{base_url}/cars/plates", 
                                   json=plates_payload,
                                   headers={"Content-Type": "application/json"}) as response:
                if response.status == 200:
                    data = await response.json()
                    elapsed = time.time() - start_time
                    print(f"✅ /cars/plates: {response.status} - {elapsed:.3f}s")
                    print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                else:
                    print(f"❌ /cars/plates: {response.status} - {await response.text()}")
    except Exception as e:
        print(f"❌ /cars/plates error: {e}")
    
    # Test /cars/path endpoint
    print("\n🛣️  Testing /cars/path endpoint...")
    path_payload = {
        "plate": "ABC1234",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    }
    
    start_time = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{base_url}/cars/path", 
                                   json=path_payload,
                                   headers={"Content-Type": "application/json"}) as response:
                if response.status == 200:
                    data = await response.json()
                    elapsed = time.time() - start_time
                    print(f"✅ /cars/path: {response.status} - {elapsed:.3f}s")
                    print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                else:
                    print(f"❌ /cars/path: {response.status} - {await response.text()}")
    except Exception as e:
        print(f"❌ /cars/path error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
