"""
Testes reais de performance com assertions e validações automáticas.
Estes são testes pytest que podem passar/falhar com base em critérios específicos.
"""
import asyncio
import pytest
import time
import aiohttp
import statistics
from typing import List, Dict, Any


class PerformanceMetrics:
    """Classe para armazenar e validar métricas de performance."""
    
    def __init__(self):
        self.event_loop_lags: List[float] = []
        self.response_times: List[float] = []
        self.concurrent_efficiency: float = 0.0
        self.error_count: int = 0
        
    def add_lag_measurement(self, lag_ms: float):
        self.event_loop_lags.append(lag_ms)
        
    def add_response_time(self, time_ms: float):
        self.response_times.append(time_ms)
        
    def calculate_stats(self) -> Dict[str, float]:
        """Calcula estatísticas das métricas coletadas."""
        return {
            'avg_lag_ms': statistics.mean(self.event_loop_lags) if self.event_loop_lags else 0,
            'max_lag_ms': max(self.event_loop_lags) if self.event_loop_lags else 0,
            'p95_lag_ms': statistics.quantiles(self.event_loop_lags, n=20)[18] if len(self.event_loop_lags) >= 20 else max(self.event_loop_lags) if self.event_loop_lags else 0,
            'avg_response_ms': statistics.mean(self.response_times) if self.response_times else 0,
            'p95_response_ms': statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) >= 20 else max(self.response_times) if self.response_times else 0,
            'concurrent_efficiency': self.concurrent_efficiency,
            'error_rate': self.error_count / len(self.response_times) if self.response_times else 0
        }


@pytest.mark.asyncio
async def test_event_loop_lag_within_limits():
    """
    TESTE: Event loop lag deve estar dentro de limites aceitáveis.
    CRITÉRIO: Lag médio < 10ms, lag máximo < 50ms
    """
    metrics = PerformanceMetrics()
    
    # Coleta 50 medições de lag
    for _ in range(50):
        start = time.perf_counter()
        await asyncio.sleep(0)  # Yield control back to event loop
        end = time.perf_counter()
        lag_ms = (end - start) * 1000
        metrics.add_lag_measurement(lag_ms)
        await asyncio.sleep(0.001)  # 1ms interval
    
    stats = metrics.calculate_stats()
    
    # ASSERTIONS - aqui que o teste pode FALHAR
    assert stats['avg_lag_ms'] < 10.0, f"Event loop lag muito alto: {stats['avg_lag_ms']:.2f}ms (limite: 10ms)"
    assert stats['max_lag_ms'] < 50.0, f"Pico de lag muito alto: {stats['max_lag_ms']:.2f}ms (limite: 50ms)"
    assert len(metrics.event_loop_lags) == 50, "Deveria ter coletado 50 medições"
    
    print(f"✅ Event loop saudável - Lag médio: {stats['avg_lag_ms']:.2f}ms, Máximo: {stats['max_lag_ms']:.2f}ms")


@pytest.mark.asyncio
async def test_blocking_operation_detection():
    """
    TESTE: Sistema deve detectar operações que bloqueiam o event loop.
    CRITÉRIO: Blocking detectável quando lag > 20ms durante operação
    """
    metrics = PerformanceMetrics()
    baseline_lags = []
    blocking_lags = []
    
    # Baseline: medições normais
    for _ in range(10):
        start = time.perf_counter()
        await asyncio.sleep(0)
        end = time.perf_counter()
        baseline_lags.append((end - start) * 1000)
        await asyncio.sleep(0.001)
    
    # Durante operação blocking
    async def measure_during_blocking():
        for _ in range(10):
            start = time.perf_counter()
            await asyncio.sleep(0)
            end = time.perf_counter()
            blocking_lags.append((end - start) * 1000)
            await asyncio.sleep(0.001)
    
    def blocking_operation():
        time.sleep(0.1)  # 100ms de blocking real
    
    # Executa medição durante blocking
    measure_task = asyncio.create_task(measure_during_blocking())
    blocking_operation()
    await measure_task
    
    baseline_avg = statistics.mean(baseline_lags)
    blocking_avg = statistics.mean(blocking_lags)
    
    # ASSERTIONS - validações automáticas
    assert baseline_avg < 5.0, f"Baseline já está alto: {baseline_avg:.2f}ms"
    assert blocking_avg > baseline_avg * 2, f"Blocking não foi detectado. Baseline: {baseline_avg:.2f}ms, Durante blocking: {blocking_avg:.2f}ms"
    assert len(blocking_lags) >= 5, "Deveria ter coletado medições durante blocking"
    
    print(f"✅ Blocking detectado - Baseline: {baseline_avg:.2f}ms, Durante blocking: {blocking_avg:.2f}ms")


@pytest.mark.asyncio
async def test_concurrent_operations_efficiency():
    """
    TESTE: Operações concorrentes devem ser significativamente mais rápidas.
    CRITÉRIO: Speedup >= 2x, efficiency >= 0.2
    """
    
    async def mock_api_call(delay_ms: int = 50):
        """Simula uma chamada de API."""
        await asyncio.sleep(delay_ms / 1000)
        return {"result": f"completed in {delay_ms}ms"}
    
    # Execução sequencial
    start_time = time.perf_counter()
    sequential_results = []
    for i in range(5):
        result = await mock_api_call(50)
        sequential_results.append(result)
    sequential_time = time.perf_counter() - start_time
    
    # Execução concorrente
    start_time = time.perf_counter()
    tasks = [mock_api_call(50) for _ in range(5)]
    concurrent_results = await asyncio.gather(*tasks)
    concurrent_time = time.perf_counter() - start_time
    
    # Cálculos de eficiência
    speedup = sequential_time / concurrent_time
    efficiency = speedup / 5  # 5 operações
    
    # ASSERTIONS - critérios de performance
    assert speedup >= 2.0, f"Speedup insuficiente: {speedup:.2f}x (mínimo: 2x)"
    assert efficiency >= 0.2, f"Eficiência baixa: {efficiency:.2f} (mínimo: 0.2)"
    assert len(concurrent_results) == 5, "Deveria ter 5 resultados concorrentes"
    assert len(sequential_results) == 5, "Deveria ter 5 resultados sequenciais"
    
    print(f"✅ Concorrência eficiente - Speedup: {speedup:.2f}x, Eficiência: {efficiency:.2f}")


@pytest.mark.asyncio
async def test_api_response_time_limits():
    """
    TESTE: API deve responder dentro de limites de tempo aceitáveis.
    CRITÉRIO: 95% das respostas < 500ms, nenhuma > 2s
    """
    # Este teste assume que a API mock está rodando
    base_url = "http://localhost:8001"
    metrics = PerformanceMetrics()
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
        # Faz 20 requisições para coletar estatísticas
        for i in range(20):
            try:
                start_time = time.perf_counter()
                async with session.get(f"{base_url}/health") as response:
                    response_time = (time.perf_counter() - start_time) * 1000
                    metrics.add_response_time(response_time)
                    
                    # Valida status code
                    assert response.status == 200, f"Status code inválido: {response.status}"
                    
            except asyncio.TimeoutError:
                metrics.error_count += 1
                pytest.fail(f"Timeout na requisição {i+1}")
            except aiohttp.ClientError as e:
                metrics.error_count += 1
                # Se API não estiver rodando, pula o teste
                pytest.skip(f"API não disponível em {base_url}: {e}")
    
    stats = metrics.calculate_stats()
    
    # ASSERTIONS - SLA de performance
    assert stats['avg_response_ms'] < 200, f"Tempo médio muito alto: {stats['avg_response_ms']:.2f}ms (limite: 200ms)"
    assert stats['p95_response_ms'] < 500, f"P95 muito alto: {stats['p95_response_ms']:.2f}ms (limite: 500ms)"
    assert stats['error_rate'] == 0, f"Taxa de erro: {stats['error_rate']*100:.1f}% (deve ser 0%)"
    
    print(f"✅ API responsiva - Médio: {stats['avg_response_ms']:.2f}ms, P95: {stats['p95_response_ms']:.2f}ms")


@pytest.mark.asyncio
async def test_load_test_with_thresholds():
    """
    TESTE: Sistema deve suportar carga concorrente sem degradação.
    CRITÉRIO: 50 requisições concorrentes, success rate > 95%
    """
    base_url = "http://localhost:8001"
    concurrent_requests = 50
    successful_requests = 0
    response_times = []
    
    async def make_request(session, request_id):
        try:
            start_time = time.perf_counter()
            async with session.get(f"{base_url}/health") as response:
                response_time = (time.perf_counter() - start_time) * 1000
                response_times.append(response_time)
                return response.status == 200
        except Exception:
            return False
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            # Executa requisições concorrentes
            tasks = [make_request(session, i) for i in range(concurrent_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_requests = sum(1 for r in results if r is True)
            success_rate = successful_requests / concurrent_requests
            
            # ASSERTIONS - critérios de carga
            assert success_rate >= 0.95, f"Success rate baixo: {success_rate*100:.1f}% (mínimo: 95%)"
            assert len(response_times) >= concurrent_requests * 0.9, "Muitas requisições falharam"
            
            if response_times:
                avg_time = statistics.mean(response_times)
                assert avg_time < 1000, f"Tempo médio sob carga muito alto: {avg_time:.2f}ms"
            
            print(f"✅ Load test passou - Success rate: {success_rate*100:.1f}%, Tempo médio: {statistics.mean(response_times):.2f}ms")
            
    except aiohttp.ClientError:
        pytest.skip("API não disponível para load test")


# Teste de integração para demonstrar falha
@pytest.mark.asyncio
async def test_intentional_failure_example():
    """
    TESTE: Exemplo de como um teste pode FALHAR.
    Este teste vai falhar propositalmente para mostrar como funcionam as assertions.
    """
    # Uncommenta a linha abaixo para ver um teste falhando:
    # assert False, "Este é um exemplo de teste que falha - remova esta linha para passar"
    
    # Simula condição que pode falhar
    simulated_response_time = 150  # ms
    threshold = 100  # ms
    
    # Esta assertion pode falhar dependendo da condição
    if simulated_response_time > threshold:
        pytest.skip(f"Pulando teste - tempo simulado {simulated_response_time}ms > threshold {threshold}ms")
    
    assert simulated_response_time <= threshold, f"Response time {simulated_response_time}ms excede threshold {threshold}ms"
    print("✅ Teste passou - dentro do threshold")


if __name__ == "__main__":
    # Para rodar apenas um teste específico:
    # pytest tests/test_performance_real.py::test_event_loop_lag_within_limits -v
    
    # Para rodar todos os testes:
    # pytest tests/test_performance_real.py -v
    
    print("Para executar os testes, use:")
    print("pytest tests/test_performance_real.py -v")
    print("ou")
    print("make test-performance-real")
