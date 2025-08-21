"""
Exemplo de teste que FALHA propositalmente para demonstrar a diferença.
"""
import pytest
import asyncio
import time


@pytest.mark.asyncio
async def test_that_will_fail():
    """
    TESTE: Este teste VAI FALHAR para mostrar como funcionam assertions.
    """
    # Simula uma operação com tempo alto
    start = time.perf_counter()
    await asyncio.sleep(0.1)  # 100ms
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    # ASSERTION que vai falhar
    assert elapsed_ms < 50, f"Operação muito lenta: {elapsed_ms:.2f}ms (limite: 50ms)"


@pytest.mark.asyncio
async def test_event_loop_lag_strict():
    """
    TESTE: Event loop lag com limite muito restritivo (vai falhar).
    """
    lags = []
    for _ in range(10):
        start = time.perf_counter()
        await asyncio.sleep(0)
        end = time.perf_counter()
        lag_ms = (end - start) * 1000
        lags.append(lag_ms)
    
    avg_lag = sum(lags) / len(lags)
    
    # Limite muito restritivo que provavelmente vai falhar
    assert avg_lag < 0.01, f"Event loop lag muito alto: {avg_lag:.3f}ms (limite rígido: 0.01ms)"


if __name__ == "__main__":
    print("Para ver testes falhando, execute:")
    print("pytest tests/test_failing_examples.py -v")
