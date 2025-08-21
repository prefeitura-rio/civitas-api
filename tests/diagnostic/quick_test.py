#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Event Loop Test - Quick Version
"""

import asyncio
import time


async def test_basic_event_loop():
    """Test basic event loop functionality."""
    print("✅ Testing basic event loop...")
    
    # Test 1: Basic async sleep
    start = time.perf_counter()
    await asyncio.sleep(0.1)
    elapsed = time.perf_counter() - start
    print(f"   asyncio.sleep(0.1): {elapsed:.3f}s")
    
    # Test 2: Event loop lag measurement
    print("✅ Measuring event loop lag...")
    measurements = []
    
    for i in range(10):  # Just 10 measurements
        start = time.perf_counter()
        await asyncio.sleep(0)  # Yield control
        end = time.perf_counter()
        lag = (end - start) * 1000  # Convert to ms
        measurements.append(lag)
        print(f"   Measurement {i+1}: {lag:.2f}ms")
    
    avg_lag = sum(measurements) / len(measurements)
    max_lag = max(measurements)
    
    print(f"\n📊 Results:")
    print(f"   Average lag: {avg_lag:.2f}ms")
    print(f"   Max lag: {max_lag:.2f}ms")
    print(f"   Status: {'✅ Good' if avg_lag < 10 else '⚠️  High' if avg_lag < 50 else '❌ Bad'}")


async def test_blocking_simulation():
    """Test blocking operation simulation."""
    print("\n🔍 Testing blocking operation simulation...")
    
    def blocking_operation(duration=0.1):
        """Simulate a blocking operation."""
        time.sleep(duration)  # This blocks!
        return f"Blocked for {duration}s"
    
    # Measure lag during blocking operation
    print("   Starting lag measurement...")
    measurements = []
    
    # Start measurement task
    async def measure_lag():
        for i in range(5):
            start = time.perf_counter()
            await asyncio.sleep(0)
            end = time.perf_counter()
            lag = (end - start) * 1000
            measurements.append(lag)
            await asyncio.sleep(0.02)  # 20ms interval
    
    # Run blocking operation and measurement concurrently
    lag_task = asyncio.create_task(measure_lag())
    
    # This will block the event loop
    start = time.perf_counter()
    result = blocking_operation(0.05)  # 50ms block
    block_time = time.perf_counter() - start
    
    # Wait for measurements to complete
    await lag_task
    
    if measurements:
        avg_lag = sum(measurements) / len(measurements)
        max_lag = max(measurements)
        
        print(f"   Blocking operation: {block_time:.3f}s")
        print(f"   Event loop lag during block: {avg_lag:.2f}ms avg, {max_lag:.2f}ms max")
        print(f"   Status: {'❌ Blocking detected!' if max_lag > 40 else '✅ No significant blocking'}")
    else:
        print("   No lag measurements collected")


async def test_concurrent_operations():
    """Test concurrent operations."""
    print("\n⚡ Testing concurrent operations...")
    
    async def mock_api_call(delay=0.1, name=""):
        """Mock API call."""
        await asyncio.sleep(delay)
        return f"API call {name} completed"
    
    # Sequential execution
    print("   Sequential execution:")
    start = time.perf_counter()
    for i in range(3):
        result = await mock_api_call(0.05, f"seq-{i}")
        print(f"     {result}")
    sequential_time = time.perf_counter() - start
    
    # Concurrent execution
    print("   Concurrent execution:")
    start = time.perf_counter()
    tasks = [mock_api_call(0.05, f"conc-{i}") for i in range(3)]
    results = await asyncio.gather(*tasks)
    concurrent_time = time.perf_counter() - start
    
    for result in results:
        print(f"     {result}")
    
    speedup = sequential_time / concurrent_time if concurrent_time > 0 else 0
    print(f"\n   Sequential: {sequential_time:.3f}s")
    print(f"   Concurrent: {concurrent_time:.3f}s")
    print(f"   Speedup: {speedup:.1f}x")
    print(f"   Status: {'✅ Good concurrency' if speedup > 2.5 else '⚠️  Poor concurrency'}")


async def main():
    """Main test function."""
    print("🚀 Simple Event Loop Test")
    print("=" * 50)
    
    try:
        await test_basic_event_loop()
        await test_blocking_simulation()
        await test_concurrent_operations()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
