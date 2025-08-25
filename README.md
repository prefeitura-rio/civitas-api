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

```bash
# Rodar a API
poetry run task serve

# Com as variáveis de ambiente
INFISICAL_TOKEN=your_token INFISICAL_ADDRESS=your_address ENVIRONMENT=dev poetry run task serve
```

## 🧪 Testes

### Comando Principal

```bash
# Todos os testes unitários isolados (rápido, sem configuração de ambiente)
poetry run task test-unit-isolated
```

### Outros Testes

```bash
# Testes de performance (CI)
poetry run task test

# Diagnósticos locais
poetry run task test-eventloop
```

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

### 🧪 Testes

O projeto possui uma suíte de testes abrangente com **82+ testes** cobrindo diferentes aspectos da aplicação:

#### Tipos de Testes

**🚀 Testes Unitários Isolados (`tests/unit/*_isolated.py`) - NOVOS**
- **Validação de CPF/CNPJ/Placas**: 17 testes cobrindo toda lógica de validação brasileira
- **Funções Auxiliares**: 24 testes para utilitários (chunking, comparação, etc.)
- **Execução Rápida**: Sem dependências externas, execução em ~0.02 segundos
- **Auto-contidos**: Não requerem configuração de ambiente

**📊 Testes de Performance (`tests/performance/`)**
- **Testes de Performance Assíncrona**: 13 testes verificando comportamento concorrente real
- **Operações de Banco**: Simulação de consultas, escritas e transações assíncronas
- **Chamadas API Externas**: Testes de concorrência para requisições HTTP
- **Comparação Sequencial vs Concorrente**: Medição de speedup (2-10x mais rápido)
- **Pool de Conexões**: Simulação realística de pools de banco e API
- **Tratamento de Exceções**: Verificação que erros não quebram concorrência
- **Processamento em Lotes**: Validação de estratégias de batch processing

**🔧 Testes Unitários Tradicionais (`tests/unit/`)**
- **Validação de Placas**: Testa a lógica real de validação (`validate_plate`) extraída de `app.utils`
- **Tratamento de Erros da API**: Simula cenários de erro (400, 404, 500, 429) com mocking
- **Lógica de Negócio Real**: Testa as funções reais dos endpoints sem carregar a aplicação completa
- **Casos Extremos**: Unicode, caracteres especiais, performance sob carga

**🏗️ Testes de Integração de Negócio**
- **Fluxo Completo de Endpoints**: Simula o comportamento real dos endpoints de placas
- **Normalização de Dados**: Valida conversão para maiúsculas e formatação
- **Múltiplas Placas**: Testa processamento em lote com validação individual

#### Executando os Testes

```bash
# Testes isolados (recomendado para desenvolvimento)
poetry run task test-unit-isolated    # Todos os 41 testes isolados

# Todos os testes do projeto
poetry run task test

# Apenas testes unitários tradicionais
poetry run task test-unit

# Apenas testes de performance (13 testes concorrentes)
poetry run task test-performance

# Testes específicos
poetry run task test-plates    # Validação de placas
poetry run task test-errors    # Tratamento de erros
poetry run task test-path      # Lógica de rotas

# Com cobertura de código
poetry run task test-coverage
```

#### Funcionalidades Testadas

**✅ Validação de Documentos Brasileiros (Novos Testes Isolados)**
- **CPF**: Validação completa com dígitos verificadores, formatos com/sem máscara
- **CNPJ**: Validação empresarial brasileira, suporte a formatação automática
- **Placas de Veículos**:
  - **Formato Antigo**: ABC1234 (3 letras + 4 dígitos)
  - **Formato Mercosul**: ABC1D23 (3 letras + 1 dígito + 1 letra + 2 dígitos)
  - **Normalização**: Conversão automática para maiúsculas
  - **Casos Inválidos**: Formatos incorretos, caracteres especiais, tamanhos errados

**🔧 Funções Auxiliares (Novos Testes Isolados)**
- **Processamento de Localização**: Chunking, agrupamento por viagem
- **Comparação de Esquemas**: Validação profunda de estruturas de dados
- **Mapeamento HTTP**: Conversão de métodos para ações CRUD

**⚡ Performance e Concorrência**
- **Processamento Assíncrono**: Até 50 consultas simultâneas
- **Validação em Lote**: 1000+ placas em menos de 1 segundo
- **Pool de Conexões**: Simulação de ambiente de produção

**🛡️ Tratamento de Erros**
- **HTTP 400**: Formato de placa inválido
- **HTTP 404**: Placa não encontrada
- **HTTP 429**: Rate limiting
- **HTTP 500**: Erros de servidor/banco
- **Timeout**: Simulação de timeouts de rede

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


---

**Desenvolvido com ❤️ pela equipe da Prefeitura do Rio de Janeiro**
