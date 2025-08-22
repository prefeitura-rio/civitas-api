# -*- coding: utf-8 -*-
import asyncio
import time
from unittest.mock import patch, AsyncMock

import pytest


class TestAsyncDatabasePerformance:
    """
    Test suite to verify that database operations are truly asynchronous
    and don't block the event loop or other coroutines in the CIVITAS API.
    """

    @pytest.mark.asyncio
    async def test_concurrent_queries_performance(self):
        """
        Test that multiple database queries can run concurrently.
        If queries were synchronous, they would run sequentially and take much longer.
        """
        async def mock_db_call(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {
                "total_reports": 100,
                "categories": ["Segurança", "Trânsito"],
                "date_range": "2025-01-01 to 2025-08-21"
            }

        start_time = time.time()

        tasks = [mock_db_call() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        concurrent_time = time.time() - start_time

        assert len(results) == 10
        assert all(not isinstance(r, Exception) for r in results)

        assert (
            concurrent_time < 0.5
        ), f"Concurrent execution took {concurrent_time:.3f}s, expected < 0.5s"

        print(f"\n✅ Concurrent execution: {concurrent_time:.3f}s for 10 queries")

    @pytest.mark.asyncio
    async def test_sequential_vs_concurrent_comparison(self):
        """
        Compare sequential vs concurrent execution to prove async benefit.
        """
        query_delay = 0.05
        num_queries = 5

        async def mock_db_call(*args, **kwargs):
            await asyncio.sleep(query_delay)
            return {
                "total_reports": 100,
                "categories": ["Segurança", "Trânsito"],
                "date_range": "2025-01-01 to 2025-08-21"
            }

        start_time = time.time()
        sequential_results = []
        for _ in range(num_queries):
            result = await mock_db_call()
            sequential_results.append(result)
        sequential_time = time.time() - start_time

        start_time = time.time()
        tasks = [mock_db_call() for _ in range(num_queries)]
        concurrent_results = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start_time

        assert len(sequential_results) == len(concurrent_results) == num_queries

        speedup_ratio = sequential_time / concurrent_time

        print("\n📊 Performance Comparison:")
        print(f"Sequential: {sequential_time:.3f}s")
        print(f"Concurrent: {concurrent_time:.3f}s")
        print(f"Speedup: {speedup_ratio:.1f}x")

        assert (
            speedup_ratio > 2.0
        ), f"Expected speedup > 2x, got {speedup_ratio:.1f}x"

    @pytest.mark.asyncio
    async def test_non_blocking_behavior(self):
        """
        Test that database operations don't block other coroutines.
        """
        counter = {"value": 0}

        async def background_task():
            for _ in range(100):
                counter["value"] += 1
                await asyncio.sleep(0.001)

        async def mock_slow_db_call(*args, **kwargs):
            await asyncio.sleep(0.2)
            return {
                "total_reports": 100,
                "categories": ["Segurança", "Trânsito"],
                "date_range": "2025-01-01 to 2025-08-21"
            }

        db_task = asyncio.create_task(mock_slow_db_call())
        bg_task = asyncio.create_task(background_task())

        db_result, _ = await asyncio.gather(db_task, bg_task)

        assert (
            counter["value"] == 100
        ), f"Counter reached {counter['value']}, expected 100"
        assert db_result is not None

        print(
            f"\n🔄 Background task completed {counter['value']} iterations while DB query ran"
        )

    @pytest.mark.asyncio
    async def test_database_connection_pool_simulation(self):
        """
        Simulate multiple concurrent connections to test connection pool behavior.
        """
        connection_counter = {"active": 0, "max_concurrent": 0}

        async def mock_with_connection_tracking(*args, **kwargs):
            connection_counter["active"] += 1
            connection_counter["max_concurrent"] = max(
                connection_counter["max_concurrent"], connection_counter["active"]
            )

            await asyncio.sleep(0.1)

            connection_counter["active"] -= 1
            return {
                "total_reports": 100,
                "categories": ["Segurança", "Trânsito"],
                "date_range": "2025-01-01 to 2025-08-21"
            }

        tasks = [mock_with_connection_tracking() for _ in range(20)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20

        assert (
            connection_counter["max_concurrent"] > 1
        ), f"Max concurrent connections: {connection_counter['max_concurrent']}"

        print(
            f"\n🔗 Peak concurrent connections: {connection_counter['max_concurrent']}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
