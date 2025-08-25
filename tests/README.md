# 🧪 Comandos de Teste - CIVITAS API

Este documento descreve os comandos de teste disponíveis via `poetry run task`.

## 📋 Comandos Principais

### Testes Básicos
```bash
# Rodar todos os testes com output resumido
poetry run task test

# Testes rápidos (exclui testes que demoram muito)
poetry run task test-fast

# Testes silenciosos (apenas resultado final)
poetry run task test-quiet
```

### Testes por Categoria
```bash
# Apenas testes unitários
poetry run task test-unit

# Apenas testes de performance/async
poetry run task test-performance
```

### Testes Específicos
```bash
# Testes de validação de placas
poetry run task test-plates

# Testes de tratamento de erros da API
poetry run task test-errors

# Testes de funcionalidades de path
poetry run task test-path
```

### Testes com Cobertura
```bash
# Gerar relatório de cobertura em HTML
poetry run task test-coverage
```

## 📊 Resumo dos Testes

### 🧪 **Testes Unitários** (`tests/unit/`)
- **test_cars_plates.py**: 12 testes - Validação de placas brasileiras
- **test_api_errors.py**: 12 testes - Casos de erro e edge cases
- **test_cars_path.py**: 2 testes - Funcionalidades de path

### ⚡ **Testes de Performance** (`tests/performance/`)
- **test_async_db_performance.py**: 4 testes - Performance assíncrona

### 🔧 **Utilitários de Teste**
- **conftest.py**: Fixtures compartilhadas
- **utils/plate_validator.py**: Validador centralizado

## ⏱️ Tempos de Execução

| Comando | Testes | Tempo Aproximado |
|---------|--------|------------------|
| `test-fast` | 29 | ~0.9s |
| `test-plates` | 12 | ~0.13s |
| `test-performance` | 4 | ~0.73s |
| `test-errors` | 11 | ~1s (exclui timeout) |
| `test-path` | 2 | ~0.01s |

## 💡 Dicas

- Use `test-fast` para desenvolvimento rápido
- Use `test-coverage` para verificar cobertura de código
- Use comandos específicos para debug de área específica
- O teste de timeout (`test_timeout_handling`) demora ~5s por design

## 🚀 Execução em CI/CD

Para pipelines de CI/CD, recomenda-se:
```bash
poetry run task test-fast  # Para feedback rápido
poetry run task test-coverage  # Para cobertura completa
```
