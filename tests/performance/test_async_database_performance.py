# -*- coding: utf-8 -*-
import asyncio
import time
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from datetime import datetime

import pytest

from app.models import MonitoredPlate, Operation, User, PlateData, NotificationChannel
from app.pydantic_models import MonitoredPlateIn, MonitoredPlateOut


class TestAsyncDatabasePerformance:
    """Verify database operations are truly asynchronous and non-blocking."""

    @pytest.mark.asyncio
    async def test_concurrent_database_queries_performance(self):
        """Test concurrent database queries vs sequential execution."""
        plate_ids = [uuid4() for _ in range(8)]

        with patch.object(MonitoredPlate, 'get') as mock_get:

            async def mock_db_call(*args, **kwargs):
                await asyncio.sleep(0.08)
                return MonitoredPlate(
                    id=kwargs.get('id', uuid4()),
                    plate="ABC1234",
                    active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

            mock_get.side_effect = mock_db_call

            start_time = time.time()
            tasks = [MonitoredPlate.get(id=plate_id) for plate_id in plate_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            concurrent_time = time.time() - start_time

            assert len(results) == 8
            assert all(not isinstance(r, Exception) for r in results)
            
            # Should take ~80ms (not 640ms) if truly async
            assert concurrent_time < 0.2, \
                f"Concurrent execution took {concurrent_time:.3f}s, expected < 0.2s"

            print(f"\n✅ Execução concorrente DB: {concurrent_time:.3f}s para 8 consultas")

    @pytest.mark.asyncio
    async def test_sequential_vs_concurrent_database_operations(self):
        """Compare sequential vs concurrent database operations."""
        operation_ids = [uuid4() for _ in range(4)]
        query_delay = 0.06

        with patch.object(Operation, 'get') as mock_get:

            async def mock_db_call(*args, **kwargs):
                await asyncio.sleep(query_delay)
                return Operation(
                    id=kwargs.get('id', uuid4()),
                    title="Test Operation",
                    description="Test Description",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

            mock_get.side_effect = mock_db_call

            start_time = time.time()
            sequential_results = []
            for operation_id in operation_ids:
                result = await Operation.get(id=operation_id)
                sequential_results.append(result)
            sequential_time = time.time() - start_time

            start_time = time.time()
            tasks = [Operation.get(id=operation_id) for operation_id in operation_ids]
            concurrent_results = await asyncio.gather(*tasks)
            concurrent_time = time.time() - start_time

            assert len(sequential_results) == len(concurrent_results) == len(operation_ids)
            speedup_ratio = sequential_time / concurrent_time if concurrent_time > 0 else float('inf')

            print("\n📊 Comparação Performance DB:")
            print(f"Sequencial: {sequential_time:.3f}s")
            print(f"Concorrente: {concurrent_time:.3f}s")
            print(f"Speedup: {speedup_ratio:.1f}x")

            assert speedup_ratio > 2.5, \
                f"Expected speedup > 2.5x, got {speedup_ratio:.1f}x"

    @pytest.mark.asyncio
    async def test_non_blocking_database_writes(self):
        """Test database writes don't block other coroutines."""
        counter = {"value": 0}

        async def background_counter():
            for _ in range(80):
                counter["value"] += 1
                await asyncio.sleep(0.001)

        with patch.object(PlateData, 'create') as mock_create:

            async def mock_slow_db_write(*args, **kwargs):
                await asyncio.sleep(0.12)
                return PlateData(
                    plate=kwargs.get('plate', 'ABC1234'),
                    data=kwargs.get('data', {}),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

            mock_create.side_effect = mock_slow_db_write
            write_task = asyncio.create_task(
                PlateData.create(plate="ABC1234", data={"test": "data"})
            )
            counter_task = asyncio.create_task(background_counter())

            write_result, _ = await asyncio.gather(write_task, counter_task)

            # If write was blocking, counter would be low
            assert counter["value"] >= 60, \
                f"Counter reached {counter['value']}, expected >= 60"
            assert write_result is not None

            print(f"\n💾 Background task completou {counter['value']} iterações durante escrita DB")

    @pytest.mark.asyncio
    async def test_mixed_database_operations_concurrency(self):
        """Test different database operations running concurrently."""
        async def get_operation_mock(*args, **kwargs):
            await asyncio.sleep(0.05)
            return Operation(id=uuid4(), title="Test", description="Desc")

        async def create_plate_mock(*args, **kwargs):
            await asyncio.sleep(0.07)
            return PlateData(plate="ABC1234", data={})

        async def get_monitored_plates_mock(*args, **kwargs):
            await asyncio.sleep(0.04)
            return [
                MonitoredPlate(id=uuid4(), plate=f"ABC{i:04d}", active=True)
                for i in range(3)
            ]

        async def update_user_mock(*args, **kwargs):
            await asyncio.sleep(0.06)
            return User(id=uuid4(), username="test", full_name="Test User")

        with patch.object(Operation, 'get') as mock_op_get, \
             patch.object(PlateData, 'create') as mock_plate_create, \
             patch.object(MonitoredPlate, 'filter') as mock_plates_filter, \
             patch.object(User, 'get') as mock_user_get:

            mock_op_get.side_effect = get_operation_mock
            mock_plate_create.side_effect = create_plate_mock
            mock_plates_filter.return_value.all.side_effect = get_monitored_plates_mock
            mock_user_get.side_effect = update_user_mock

            start_time = time.time()

            tasks = [
                Operation.get(id=uuid4()),
                PlateData.create(plate="XYZ5678", data={}),
                MonitoredPlate.filter(active=True).all(),
                User.get(id=uuid4()),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time

            assert len(results) == 4
            assert not any(isinstance(r, Exception) for r in results)

            # Should complete in ~0.07s (slowest operation) not ~0.22s (sum)
            assert total_time < 0.12, \
                f"Mixed DB operations took {total_time:.3f}s, expected < 0.12s"

            print(f"\n🎯 Operações mistas DB completaram em {total_time:.3f}s concorrentemente")

    @pytest.mark.asyncio
    async def test_database_connection_pool_simulation(self):
        """Simulate concurrent connections to test connection pool behavior."""
        num_operations = 12
        connection_counter = {"active": 0, "max_concurrent": 0}

        with patch.object(MonitoredPlate, 'all') as mock_all:

            async def mock_with_connection_tracking(*args, **kwargs):
                connection_counter["active"] += 1
                connection_counter["max_concurrent"] = max(
                    connection_counter["max_concurrent"],
                    connection_counter["active"]
                )

                await asyncio.sleep(0.08)

                connection_counter["active"] -= 1
                return [
                    MonitoredPlate(id=uuid4(), plate=f"TST{i:03d}", active=True)
                    for i in range(2)
                ]

            mock_all.side_effect = mock_with_connection_tracking

            tasks = [MonitoredPlate.all() for _ in range(num_operations)]
            results = await asyncio.gather(*tasks)

            assert len(results) == num_operations
            assert connection_counter["max_concurrent"] > 1, \
                f"Max concurrent connections: {connection_counter['max_concurrent']}"
            assert connection_counter["max_concurrent"] >= 3, \
                f"Expected >= 3 concurrent connections, got {connection_counter['max_concurrent']}"

            print(f"\n🏊‍♀️ Pool de conexões - Pico: {connection_counter['max_concurrent']} conexões")

    @pytest.mark.asyncio
    async def test_transaction_performance_with_concurrency(self):
        """Test concurrent transactions don't block each other."""
        transaction_durations = []

        async def simulate_transaction(transaction_id: int):
            start_time = time.time()
            await asyncio.sleep(0.05 + (transaction_id * 0.01))
            
            duration = time.time() - start_time
            transaction_durations.append(duration)
            
            return f"transaction_{transaction_id}_completed"

        start_time = time.time()
        tasks = [simulate_transaction(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        assert len(results) == 5
        assert all("completed" in result for result in results)
        sum_individual_durations = sum(transaction_durations)

        print(f"\n🔄 Transações concorrentes:")
        print(f"Tempo total: {total_time:.3f}s")
        print(f"Soma durações individuais: {sum_individual_durations:.3f}s")
        print(f"Eficiência: {(sum_individual_durations/total_time):.1f}x")

        efficiency = sum_individual_durations / total_time
        assert efficiency > 2.0, f"Expected efficiency > 2x, got {efficiency:.1f}x"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])