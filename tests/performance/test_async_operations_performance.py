# -*- coding: utf-8 -*-
import asyncio
import time
from unittest.mock import patch, AsyncMock
from uuid import uuid4

import pytest

from app.pydantic_models import CortexPlacaOut


class TestAsyncOperationsPerformance:
    """Verify async operations are truly asynchronous and non-blocking."""

    @pytest.mark.asyncio
    async def test_concurrent_external_api_calls(self):
        """Test concurrent external API calls."""
        num_calls = 5
        
        with patch("app.utils.cortex_request") as mock_cortex:

            async def mock_api_call(*args, **kwargs):
                await asyncio.sleep(0.1)
                return True, {
                    "placa": "ABC1234",
                    "nomeProprietario": "Test Owner",
                    "municipioPlaca": "Rio de Janeiro",
                    "ufEmplacamento": "RJ",
                }

            mock_cortex.side_effect = mock_api_call

            start_time = time.time()
            from app.utils import cortex_request
            tasks = [cortex_request("ABC1234", "12345678900") for _ in range(num_calls)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            concurrent_time = time.time() - start_time

            assert len(results) == num_calls
            assert all(not isinstance(r, Exception) for r in results if r is not None)
            assert concurrent_time < 0.2, \
                f"Concurrent execution took {concurrent_time:.3f}s, expected < 0.2s"

            print(f"\n✅ API concorrente: {concurrent_time:.3f}s para {num_calls} chamadas")

    @pytest.mark.asyncio
    async def test_sequential_vs_concurrent_api_calls(self):
        """Compare sequential vs concurrent API calls."""
        num_calls = 3
        query_delay = 0.05
        
        with patch("app.utils.cortex_request") as mock_cortex:

            async def mock_api_call(*args, **kwargs):
                await asyncio.sleep(query_delay)
                return True, {
                    "placa": "ABC1234",
                    "nomeProprietario": "Test",
                    "municipioPlaca": "Rio de Janeiro",
                    "ufEmplacamento": "RJ",
                }

            mock_cortex.side_effect = mock_api_call

            from app.utils import cortex_request

            start_time = time.time()
            sequential_results = []
            for _ in range(num_calls):
                result = await cortex_request("ABC1234", "12345678900")
                sequential_results.append(result)
            sequential_time = time.time() - start_time

            start_time = time.time()
            tasks = [cortex_request("ABC1234", "12345678900") for _ in range(num_calls)]
            concurrent_results = await asyncio.gather(*tasks)
            concurrent_time = time.time() - start_time

            assert len(sequential_results) == len(concurrent_results) == num_calls
            speedup_ratio = sequential_time / concurrent_time if concurrent_time > 0 else float('inf')

            print("\n📊 Comparação API Performance:")
            print(f"Sequencial: {sequential_time:.3f}s")
            print(f"Concorrente: {concurrent_time:.3f}s")  
            print(f"Speedup: {speedup_ratio:.1f}x")

            assert speedup_ratio > 2.0, \
                f"Expected speedup > 2x, got {speedup_ratio:.1f}x"

    @pytest.mark.asyncio
    async def test_non_blocking_operations(self):
        """Test async operations don't block other coroutines."""
        counter = {"value": 0}

        async def background_task():
            for _ in range(50):
                counter["value"] += 1
                await asyncio.sleep(0.002)

        async def slow_operation():
            await asyncio.sleep(0.15)
            return "completed"

        slow_task = asyncio.create_task(slow_operation())
        bg_task = asyncio.create_task(background_task())

        slow_result, _ = await asyncio.gather(slow_task, bg_task)

        # If slow operation was blocking, counter would be low
        assert counter["value"] >= 40, \
            f"Counter reached {counter['value']}, expected >= 40"
        assert slow_result == "completed"

        print(f"\n🔄 Background task completou {counter['value']} iterações durante operação lenta")

    @pytest.mark.asyncio
    async def test_mixed_async_operations_concurrency(self):
        """Test different async operations run concurrently."""
        
        async def fast_operation():
            await asyncio.sleep(0.03)
            return "fast_completed"

        async def medium_operation():
            await asyncio.sleep(0.06)
            return "medium_completed"
            
        async def slow_operation():
            await asyncio.sleep(0.09)
            return "slow_completed"

        start_time = time.time()

        tasks = [
            fast_operation(),
            medium_operation(),
            slow_operation(),
        ]

        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        assert len(results) == 3
        assert results == ["fast_completed", "medium_completed", "slow_completed"]
        
        # Should complete in ~0.09s (slowest) not ~0.18s (sum)
        assert total_time < 0.15, \
            f"Mixed operations took {total_time:.3f}s, expected < 0.15s"

        print(f"\n🚀 Operações mistas completaram em {total_time:.3f}s concorrentemente")

    @pytest.mark.asyncio 
    async def test_batch_processing_performance(self):
        """Test batch processing concurrency benefits."""
        items = list(range(25))
        
        async def process_item(item_id: int):
            await asyncio.sleep(0.02)
            return f"item_{item_id}_processed"

        start_time = time.time()
        processed_items = []
        for i in range(0, len(items), 10):
            batch = items[i:i + 10]
            batch_results = await asyncio.gather(*[
                process_item(item_id) for item_id in batch
            ])
            processed_items.extend(batch_results)

        batch_time = time.time() - start_time

        assert len(processed_items) == 25
        # 3 batches should take ~60ms (3 x 20ms) not ~500ms (25 x 20ms)
        assert batch_time < 0.1, \
            f"Batch processing took {batch_time:.3f}s, expected < 0.1s"

        print(f"\n📦 Processamento em lotes: {batch_time:.3f}s para {len(items)} itens")

    @pytest.mark.asyncio
    async def test_connection_pool_simulation(self):
        """Simulate connection pool patterns with concurrent connections."""
        num_connections = 15
        connection_counter = {"active": 0, "max_concurrent": 0}

        async def simulate_connection(connection_id: int):
            connection_counter["active"] += 1
            connection_counter["max_concurrent"] = max(
                connection_counter["max_concurrent"], 
                connection_counter["active"]
            )

            await asyncio.sleep(0.05)

            connection_counter["active"] -= 1
            return f"connection_{connection_id}_completed"

        tasks = [simulate_connection(i) for i in range(num_connections)]
        results = await asyncio.gather(*tasks)

        assert len(results) == num_connections
        assert connection_counter["max_concurrent"] > 1, \
            f"Max concurrent connections: {connection_counter['max_concurrent']}"
        assert connection_counter["max_concurrent"] >= 3, \
            f"Expected >= 3 concurrent connections, got {connection_counter['max_concurrent']}"

        print(f"\n🔗 Pico de conexões concorrentes: {connection_counter['max_concurrent']}")

    @pytest.mark.asyncio
    async def test_async_performance_with_exceptions(self):
        """Test exceptions don't prevent async concurrency."""
        
        async def operation_that_succeeds():
            await asyncio.sleep(0.05)
            return "success"
            
        async def operation_that_fails():
            await asyncio.sleep(0.03)
            raise ValueError("Simulated error")
            
        async def operation_that_succeeds_slow():
            await asyncio.sleep(0.08)
            return "success_slow"

        start_time = time.time()
        
        results = await asyncio.gather(
            operation_that_succeeds(),
            operation_that_fails(),
            operation_that_succeeds_slow(),
            return_exceptions=True
        )
        
        total_time = time.time() - start_time

        assert len(results) == 3
        assert results[0] == "success"
        assert isinstance(results[1], ValueError)
        assert results[2] == "success_slow"
        
        # Should complete in ~80ms (slowest operation), not sum
        assert total_time < 0.12, \
            f"Operations with exceptions took {total_time:.3f}s, expected < 0.12s"

        print(f"\n⚠️ Operações com exceções completaram em {total_time:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])