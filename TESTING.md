# Scripts de Performance Testing

Este projeto inclui vários scripts para testar performance e event loop. Use o **Makefile** para executá-los facilmente:

## Comandos Rápidos

```bash
# Ver todos os comandos
make help

# Testes essenciais
make test-eventloop     # Baseline do event loop
make test-api-mock      # API de teste (porta 8001)
make test-performance   # Load testing
make test-real         # Endpoints reais
```

## Scripts Disponíveis

### Testes Básicos de Event Loop
```bash
make test-eventloop
```
- Mede lag básico do event loop (target: < 10ms)
- Testa operações concorrentes (target: speedup > 2x)
- Simula operações blocking para validação

### API Mock para Testes
```bash
make test-api-mock
```
- Inicia API mock na porta 8001
- Endpoints que simulam problemas de blocking
- Endpoints: `/test/cars/plates`, `/test/cars/path`, `/test/concurrent`

### Testes de Performance/Load
```bash
make test-performance
```
- Executa testes de carga contra a API mock
- Mede concurrency efficiency (target: > 0.1)
- Requer API mock rodando

### Teste da API Real
```bash
make test-real
```
- Testa os endpoints reais `/cars/plates` e `/cars/path`
- Requer API principal rodando na porta 8000
- Usa payload real para validação

## Workflow Recomendado

1. **Baseline do sistema:**
   ```bash
   make test-eventloop
   ```

2. **Teste com simulação:**
   ```bash
   # Terminal 1
   make test-api-mock
   
   # Terminal 2
   make test-performance
   ```

3. **Validação final:**
   ```bash
   # Terminal 1
   make serve
   
   # Terminal 2
   make test-real
   ```

## Interpretação dos Resultados

### Event Loop Lag
- ✅ **< 10ms**: Event loop saudável
- ⚠️ **10-50ms**: Lag moderado, investigar
- ❌ **> 50ms**: Problema sério de blocking

### Concurrency Efficiency
```
efficiency = concurrent_speed / sequential_speed
```
- ✅ **> 0.2**: Excelente paralelização
- ⚠️ **0.1-0.2**: Paralelização adequada
- ❌ **< 0.1**: Possível blocking ou serialização

### Response Times
- Monitore timeouts e picos de latência
- Compare tempos entre mock e API real
- Identifique endpoints problemáticos

## Comandos Alternativos (Poetry/Python direto)

Se preferir não usar o Makefile:
## Comandos Alternativos (Poetry/Python direto)

Se preferir não usar o Makefile:

```bash
# Testes básicos
poetry run python tests/quick_test.py

# API mock
poetry run python tests/test_api.py

# Load testing
poetry run python tests/load_test.py

# Direto com Python (se tiver deps instaladas)
python tests/quick_test.py
python tests/test_api.py
python tests/load_test.py
```

## Estrutura dos Testes

- `tests/quick_test.py` - Testes básicos de event loop
- `tests/test_api.py` - API mock com simulações de blocking
- `tests/load_test.py` - Load testing e análise de concorrência
- `tests/event_loop_profiler.py` - Profiler avançado (opcional)

## Troubleshooting

**Erro "Command not found"**: Use `make help` para verificar comandos disponíveis

**API não responde**: Verifique se está rodando na porta correta:
- API principal: `http://localhost:8080`
- API mock: `http://localhost:8001`

**Testes falhando**: Verifique dependências com `make install`
