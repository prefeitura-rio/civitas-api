#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal API for testing event loop blocking issues
"""

import asyncio
import time
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Civitas Test API")


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/test/cars/plates")
async def test_cars_plates(plates_data: dict):
    """
    Simulate the /cars/plates endpoint behavior.
    
    This simulates the problematic patterns we identified:
    - External API calls in batches
    - asyncio.gather() usage
    - Potential blocking operations
    """
    plates = plates_data.get("plates", [])
    
    async def mock_external_api_call(plate: str):
        """Simulate external API call (like Cortex API)."""
        # Simulate network delay
        await asyncio.sleep(0.2)
        return {
            "plate": plate,
            "owner": f"Owner of {plate}",
            "status": "active"
        }
    
    def blocking_operation(plate: str):
        """Simulate a blocking operation (like synchronous DB call)."""
        time.sleep(0.1)  # This blocks the event loop!
        return f"Processed {plate}"
    
    # Test different patterns
    if len(plates) == 1:
        # Single plate - should be fast
        result = await mock_external_api_call(plates[0])
        return {"results": [result], "pattern": "single"}
    
    elif len(plates) <= 5:
        # Small batch - use asyncio.gather
        results = await asyncio.gather(*[
            mock_external_api_call(plate) for plate in plates
        ])
        return {"results": results, "pattern": "async_batch"}
    
    else:
        # Large batch - simulate problematic blocking pattern
        results = []
        for plate in plates:
            # Mix of async and blocking operations
            async_result = await mock_external_api_call(plate)
            blocking_result = blocking_operation(plate)  # This blocks!
            
            results.append({
                **async_result,
                "blocking_result": blocking_result
            })
        
        return {"results": results, "pattern": "mixed_blocking"}


@app.get("/test/cars/path")
async def test_cars_path(placa: str, hours: int = 1):
    """
    Simulate the /cars/path endpoint behavior.
    
    This simulates:
    - BigQuery-like operations
    - Data processing
    - Potential blocking during large queries
    """
    
    def simulate_bigquery_blocking(hours: int):
        """Simulate BigQuery blocking operation."""
        # Simulate query execution time based on time range
        sleep_time = min(hours * 0.1, 2.0)  # Max 2 seconds
        time.sleep(sleep_time)  # This blocks!
        
        # Generate fake path data
        points = []
        for i in range(hours * 10):  # 10 points per hour
            points.append({
                "timestamp": (datetime.now() - timedelta(minutes=i*6)).isoformat(),
                "latitude": -22.9068 + (i * 0.001),
                "longitude": -43.1729 + (i * 0.001),
                "speed": 30 + (i % 20)
            })
        
        return points
    
    # Simulate the blocking BigQuery operation
    start_time = time.perf_counter()
    path_data = simulate_bigquery_blocking(hours)
    query_time = time.perf_counter() - start_time
    
    # Simulate some async post-processing
    await asyncio.sleep(0.05)  # Simulate async processing
    
    return {
        "plate": placa,
        "path": path_data,
        "query_time": query_time,
        "points_count": len(path_data),
        "hours_requested": hours
    }


@app.get("/test/concurrent")
async def test_concurrent_load():
    """
    Endpoint to test concurrent behavior.
    """
    async def cpu_intensive_task():
        """Simulate CPU-intensive work."""
        # This should NOT block the event loop
        await asyncio.sleep(0.1)
        return sum(i * i for i in range(1000))
    
    def blocking_cpu_task():
        """Simulate blocking CPU work."""
        # This WILL block the event loop
        time.sleep(0.1)
        return sum(i * i for i in range(1000))
    
    # Run both patterns
    start_time = time.perf_counter()
    
    # Non-blocking pattern
    async_result = await cpu_intensive_task()
    async_time = time.perf_counter() - start_time
    
    # Blocking pattern
    start_time = time.perf_counter()
    blocking_result = blocking_cpu_task()
    blocking_time = time.perf_counter() - start_time
    
    return {
        "async_result": async_result,
        "async_time": async_time,
        "blocking_result": blocking_result,
        "blocking_time": blocking_time,
        "recommendation": "Use async pattern for better concurrency"
    }


def serve():
    """Entry point for serving the test API"""
    print("🚀 Starting Civitas Test API on http://localhost:8001")
    print("📊 Test endpoints:")
    print("  - GET  /health")
    print("  - POST /test/cars/plates")
    print("  - GET  /test/cars/path?placa=ABC1234&hours=1")
    print("  - GET  /test/concurrent")
    print("  - Docs: http://localhost:8001/docs")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    serve()
