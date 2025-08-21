# 🧪 Event Loop Performance Tests

Estes testes foram criados para identificar gargalos de performance no event loop da API Civitas, especificamente focando nos endpoints `/cars/plates` e `/cars/path` que foram identificados como potencialmente problemáticos.

## 📋 Testes Disponíveis

### 1. `simple_event_loop_test.py` 
**Teste básico de blocking do event loop**
- ✅ Não requer dependências externas
- ✅ Simula operações bloqueantes
- ✅ Mede lag do event loop
- ✅ Compara processamento concurrent vs sequential

```bash
cd /Users/gabrielseixas/.code/civitas/civitas-api
python tests/simple_event_loop_test.py
```

### 2. `api_performance_test.py`
**Teste dos endpoints reais da API**
- ✅ Testa `/cars/plates` com diferentes batch sizes
- ✅ Testa `/cars/path` com diferentes time ranges  
- ✅ Testa carga concurrent mista
- ✅ Usa apenas curl (sem dependências Python)

```bash
# 1. Primeiro, inicie a API
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. Em outro terminal, execute o teste
python tests/api_performance_test.py
```

### 3. `test_performance_event_loop.py`
**Testes pytest completos**
- 🔧 Requer pytest e httpx
- 🔧 Testes parametrizados por concorrência
- 🔧 Métricas detalhadas de performance

```bash
# Instalar dependências primeiro
poetry add --group dev pytest httpx

# Executar testes
poetry run pytest tests/test_performance_event_loop.py -v
```

### 4. `event_loop_profiler.py`
**Profiler avançado**
- 🔧 Requer aiohttp
- 🔧 Profila operações internas
- 🔧 Testa BigQuery e operações de batch

```bash
# Instalar dependências
poetry add --group dev aiohttp

# Executar profiler
python tests/event_loop_profiler.py
```

## 🚀 Como Executar os Testes

### Teste Rápido (Recomendado)
```bash
# 1. Teste básico de event loop (sem API)
python tests/simple_event_loop_test.py

# 2. Inicie a API
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Teste os endpoints (em outro terminal)
python tests/api_performance_test.py
```

### Teste Completo
```bash
# 1. Instalar dependências de teste
poetry add --group dev pytest httpx aiohttp

# 2. Executar todos os testes
poetry run pytest tests/test_performance_event_loop.py -v
python tests/event_loop_profiler.py
```

## 🔍 O Que Analisar

### 📊 Métricas Importantes

1. **Event Loop Lag**
   - ✅ Normal: < 10ms average
   - ⚠️ Atenção: 10-100ms average  
   - ❌ Problema: > 100ms average

2. **Response Times**
   - **`/cars/plates`**: < 5s para 10 placas
   - **`/cars/path`**: < 10s para 24h de dados

3. **Concurrency Efficiency**
   - ✅ Bom: < 1.0 (concurrent é melhor que sequential)
   - ⚠️ Atenção: 1.0-1.5
   - ❌ Problema: > 1.5 (concurrent pior que sequential)

4. **P95/Median Ratio**
   - ✅ Normal: < 3.0
   - ⚠️ Atenção: 3.0-10.0
   - ❌ Blocking: > 10.0

### 🚨 Sinais de Event Loop Blocking

1. **Alto Event Loop Lag** durante operações
2. **Poor Concurrency Efficiency** (concurrent slower than sequential)
3. **Alto P95/Median Ratio** nas response times
4. **Timeouts** frequentes em carga concurrent

## 🔧 Configuração de Autenticação

Os testes de API precisam de autenticação. Para configurar:

1. **Obter token de teste**:
```bash
# Fazer login na API
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

2. **Atualizar os scripts**:
   - Edite `api_performance_test.py`
   - Substitua `"Bearer your_token_here"` pelo token real

3. **Ou usar variável de ambiente**:
```bash
export CIVITAS_API_TOKEN="your_actual_token"
python tests/api_performance_test.py
```

## 📈 Interpretando Resultados

### Exemplo de Output Normal:
```
✅ Baseline event loop lag: 2.1ms avg, 15.3ms max
✅ /cars/plates - Average time: 2.3s, Concurrency efficiency: 0.8
✅ /cars/path - Average time: 4.1s, P95/median ratio: 2.1
```

### Exemplo de Output Problemático:
```
❌ Baseline event loop lag: 45.2ms avg, 250.8ms max
❌ /cars/plates - Average time: 12.8s, Concurrency efficiency: 1.8
❌ /cars/path - Average time: 25.3s, P95/median ratio: 15.4
```

## 🛠️ Próximos Passos

Baseado nos resultados dos testes:

1. **Se confirmar blocking do BigQuery**:
   - Mover queries para thread pool
   - Implementar async BigQuery client
   - Adicionar connection pooling

2. **Se confirmar blocking do PDF**:
   - Mover geração para background tasks
   - Usar process pool para CPU-intensive work
   - Implementar queue system

3. **Se confirmar batch processing issues**:
   - Limitar concorrência no `asyncio.gather()`
   - Implementar semaphore para rate limiting
   - Otimizar batch sizes

## 📝 Relatório de Bugs

Se encontrar problemas, documente:

1. **Comando executado**
2. **Output completo**
3. **Métricas específicas** (lag, response times, ratios)
4. **Condições do teste** (carga, batch size, etc.)

Exemplo:
```markdown
## Bug Report: Event Loop Blocking em /cars/plates

**Comando**: `python tests/api_performance_test.py`
**Event Loop Lag**: 127ms average, 450ms max
**Response Time**: 15.2s average para 5 placas
**Concurrency Efficiency**: 2.1 (concurrent 2x mais lento)

**Conclusão**: Operação síncrona bloqueando event loop
```

---

**⚡ Happy Testing!** 🚀
