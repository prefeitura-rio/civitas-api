# 🏛️ Civitas API

> Sistema de monitoramento e análise urbana da Prefeitura do Rio de Janeiro

Civitas é uma API FastAPI desenvolvida para gerenciar e analisar dados urbanos, incluindo monitoramento de veículos, operações de trânsito, câmeras, radares e muito mais.

## 📋 Índice

- [Características](#-características)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Executando o Projeto](#-executando-o-projeto)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [API Endpoints](#-api-endpoints)
- [Desenvolvimento](#-desenvolvimento)
- [Deploy](#-deploy)
- [Contribuição](#-contribuição)

## ✨ Características

- **FastAPI**: Framework moderno e rápido para APIs REST
- **Async/Await**: Suporte completo para operações assíncronas
- **PostgreSQL**: Banco de dados principal com Tortoise ORM
- **Redis**: Cache e rate limiting
- **BigQuery**: Integração com Google Cloud para análise de dados
- **Autenticação**: Sistema de autenticação com OIDC
- **Rate Limiting**: Controle de taxa de requisições
- **Monitoramento**: Integração com Sentry para tracking de erros
- **PDF Generation**: Geração de relatórios em PDF
- **Containerized**: Pronto para Docker e Kubernetes

## 🔧 Pré-requisitos

- Python 3.11+
- Poetry (gerenciador de dependências)
- PostgreSQL
- Redis
- Docker (opcional)
- Git

## 🚀 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/prefeitura-rio/civitas-api.git
cd civitas-api
```

### 2. Instale as dependências

```bash
# Instalar Poetry (caso não tenha)
curl -sSL https://install.python-poetry.org | python3 -

# Instalar dependências do projeto
poetry install
```

### 3. Ative o ambiente virtual

```bash
poetry shell
```

## ⚙️ Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/civitas

# Redis
REDIS_URL=redis://localhost:6379

# Logging
LOG_LEVEL=INFO

# Sentry (opcional)
SENTRY_ENABLE=false
SENTRY_DSN=your_sentry_dsn_here

# Google Cloud (para BigQuery)
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account.json

# Auth
SECRET_KEY=your_secret_key_here
```

### Configuração do Banco de Dados

```bash
# Executar migrações
aerich upgrade
```

## 🏃‍♂️ Executando o Projeto

### Scripts de Performance Testing

Este projeto inclui duas categorias de ferramentas para análise de performance:

### 📊 **Scripts Diagnósticos** (Análise e Coleta de Métricas)
```bash
# Ver todos os comandos disponíveis
make help

# Scripts de diagnóstico (sempre "passam", imprimem métricas)
make diag-eventloop     # Event loop lag measurement
make mock-api          # API mock para testes (porta 8001)
make diag-load         # Load testing diagnostics
make diag-all          # Todos os scripts diagnósticos
```

### ✅ **Testes Performance** (Pytest com Assertions)
```bash
# Testes pytest (podem PASSAR ✅ ou FALHAR ❌)
make test-perf         # Todos os testes de performance
make test-perf-fast    # Teste rápido de event loop
make test-examples     # Exemplos de testes que falham
```

### 🎯 **Quando usar cada tipo?**

| Tipo | Uso | Características |
|------|-----|----------------|
| **📊 Diagnósticos** | Investigação, debugging, coleta de métricas | Sempre "passam", output detalhado |
| **✅ Performance** | CI/CD, validação automática, SLAs | PASSAM/FALHAM, critérios específicos |

### Workflow de Testing

1. **Investigação com diagnósticos:**
   ```bash
   make diag-eventloop      # Baseline do sistema
   
   # Terminal 1: API mock
   make mock-api
   
   # Terminal 2: Load testing
   make diag-load
   ```

2. **Validação com testes pytest:**
   ```bash
   make test-perf           # Validação automática
   ```

3. **Teste da API real:**
   ```bash
   # Terminal 1: API principal
   make serve
   
   # Terminal 2: Testes nos endpoints reais
   make test-real
   ```

### Interpretação dos Resultados

#### 📊 Diagnósticos (Console Output)
- **Event Loop Lag**: < 10ms = ✅ Bom, 10-50ms = ⚠️ Alto, >50ms = ❌ Problema
- **Concurrency Efficiency**: > 0.1 = ✅ Bom, valores baixos indicam blocking
- **Response Times**: Monitore tempos elevados e timeouts

#### ✅ Testes Pytest (Pass/Fail)
- **PASSED**: Sistema atende critérios definidos
- **FAILED**: Violação de SLA, regressão detectada
- **SKIPPED**: Dependência não disponível (ex: API offline)

## Desenvolvimento

```bash
# Executar servidor de desenvolvimento
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em: `http://localhost:8000`

### Documentação da API

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Docker

```bash
# Build da imagem
docker build -t civitas-api .

# Executar container
docker run -p 8000:8000 civitas-api
```

## 📁 Estrutura do Projeto

```
civitas-api/
├── app/                        # Código principal da aplicação
│   ├── routers/               # Endpoints da API
│   │   ├── agents.py          # Gestão de agentes
│   │   ├── auth.py            # Autenticação
│   │   ├── cars.py            # Veículos
│   │   ├── operations.py      # Operações
│   │   └── ...
│   ├── services/              # Lógica de negócio
│   ├── templates/             # Templates HTML/CSS
│   ├── config/                # Configurações
│   ├── models.py              # Modelos do banco de dados
│   ├── main.py                # Aplicação principal
│   └── ...
├── migrations/                # Migrações do banco
├── k8s/                      # Manifests Kubernetes
├── scripts/                  # Scripts utilitários
├── Dockerfile               # Container configuration
├── pyproject.toml           # Dependências e configuração
└── README.md               # Este arquivo
```

## 🔗 API Endpoints

### Principais Recursos

- **`/auth`** - Autenticação e autorização
- **`/users`** - Gestão de usuários
- **`/cars`** - Monitoramento de veículos
- **`/operations`** - Operações de trânsito
- **`/radars`** - Dados de radares
- **`/cameras-cor`** - Câmeras do COR
- **`/reports`** - Relatórios e análises
- **`/agents`** - Gestão de agentes
- **`/companies`** - Empresas e frotas

### Health Check

```bash
curl http://localhost:8000/health
```

## 👨‍💻 Desenvolvimento

### Ferramentas de Qualidade de Código

```bash
# Formatação de código
poetry run black .

# Ordenação de imports
poetry run isort .

# Linting
poetry run flake8

# Executar todos os checks
poetry run pre-commit run --all-files
```

### Testes

```bash
# Executar testes
poetry run pytest

# Com coverage
poetry run pytest --cov=app
```

### Migrações

```bash
# Criar nova migração
aerich migrate

# Aplicar migrações
aerich upgrade
```

## 📝 Licença

Este projeto é propriedade da Prefeitura do Rio de Janeiro.

## 👥 Time

- **Gabriel Gazola Milan** - _Desenvolvedor Principal_ - gabriel.gazola@poli.ufrj.br

---

**Desenvolvido com ❤️ pela equipe da Prefeitura do Rio de Janeiro**
