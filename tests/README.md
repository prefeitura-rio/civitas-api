# Testes

Este diretório contém a suíte de testes para a aplicação Civitas API.

## Estrutura

```
tests/
├── __init__.py
├── conftest.py                           # Configuração de ambiente para testes
├── unit/                                # Diretório de testes unitários
│   ├── __init__.py
│   ├── test_validation_functions.py     # Testes para validação de CPF, CNPJ, placas
│   └── test_helper_functions.py         # Testes para funções utilitárias
└── README.md                           # Este arquivo
```

## Executando os Testes

### Usando Comandos Taskipy (Recomendado)

```bash
# Executar todos os testes unitários (importa código real do app/)
poetry run task test-unit-isolated

# Executar com relatório de cobertura
poetry run task test-coverage
```

### Comandos pytest Diretos

```bash
# Executar todos os testes unitários
poetry run pytest tests/unit/ -v

# Executar arquivos de teste específicos
poetry run pytest tests/unit/test_validation_functions.py -v
poetry run pytest tests/unit/test_helper_functions.py -v

# Executar com cobertura
poetry run pytest tests/unit/ --cov=app --cov-report=html -v
```

## Categorias de Testes

### 1. Funções de Validação (`test_validation_functions.py`)
Testa a lógica central de validação **importando diretamente de `app.utils`**:
- **Validação de CPF**: Validação de CPF brasileiro
- **Validação de CNPJ**: Validação de CNPJ brasileiro
- **Validação de Placas**: Validação do formato de placas de veículos brasileiros

Estes testes cobrem:
- Entradas válidas (vários formatos)
- Entradas inválidas (dígitos errados, comprimentos, formatos)
- Casos extremos (todos os dígitos iguais, caracteres especiais)

### 2. Funções Auxiliares (`test_helper_functions.py`)
Testa funções utilitárias **importando diretamente de `app.utils`**:
- **`chunk_locations()`**: Divide arrays de localização em chunks sobrepostos
- **`get_trips_chunks()`**: Agrupa pontos de localização em viagens baseado em intervalos de tempo
- **`check_schema_equality()`**: Comparação profunda de esquemas de dicionários
- **`translate_method_to_action()`**: Mapeia métodos HTTP para ações CRUD

## Abordagem de Testes Reais

Os testes neste projeto testam **o código real da aplicação**:
- **Importação direta**: `from app.utils import validate_cpf, validate_cnpj, validate_plate`
- **Testa o código real**: Não há cópias ou duplicações de código
- **Ambiente configurado**: O `conftest.py` configura automaticamente o ambiente de teste
- **Detecta regressões**: Mudanças no código real são testadas automaticamente

## Configuração de Testes

A configuração é **automática** através do `conftest.py`:
- ✅ **Ambiente de teste**: `ENVIRONMENT=test` bypassa Infisical
- ✅ **Variáveis mockadas**: Todas as variáveis de ambiente necessárias
- ✅ **HTTP requests mockadas**: Nenhuma requisição real durante os testes
- ✅ **Configuração transparente**: Desenvolvedores não precisam se preocupar

## Contribuindo

Ao adicionar novos testes:

1. **Importe diretamente**: `from app.utils import sua_funcao`
2. **Teste comportamento real**: Não copie código, importe da aplicação
3. **Siga convenções de nomenclatura**: `test_<nome_da_funcao>_<cenario>`
4. **Inclua docstrings em português**: Descreva o que cada teste valida
5. **Teste casos extremos**: Entradas vazias, formatos inválidos, condições limítrofes
6. **Confie no conftest.py**: O ambiente já está configurado automaticamente

## Resultados dos Testes

Cobertura atual dos testes **reais**:
- ✅ **Validação de CPF**: 6 casos de teste, testa `app.utils.validate_cpf`
- ✅ **Validação de CNPJ**: 5 casos de teste, testa `app.utils.validate_cnpj`
- ✅ **Validação de Placas**: 6 casos de teste, testa `app.utils.validate_plate`
- ✅ **Funções Auxiliares**: 24 casos de teste, testam `app.utils.*`

Total: **41 testes testando código real da aplicação**