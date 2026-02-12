# Civitas API

API para o APP CIVITAS.

## Estrutura do projeto

- **app/** – Código da aplicação (routers, models, config, serviços).
- **migrations/** – Arquivos de migration do Aerich (Tortoise ORM).
- **dev/** – Docker Compose e recursos para desenvolvimento local.
- **k8s/** – Manifests Kubernetes (staging e prod) para deploy no GKE.

## Arquitetura e Ambientes

### Produção (GKE)
Em produção, a aplicação roda em Kubernetes (GKE). Não utilizamos `docker-compose` nesse ambiente; o build é feito via `Dockerfile` e os serviços de banco de dados (PostgreSQL) e cache (Redis) são gerenciados externamente no cluster.

### Desenvolvimento Local
Para replicar o ambiente de produção localmente, utilizamos Docker Compose.
- **Local:** `dev/docker-compose.yml` sobe a API, Postgres e Redis.
- **Caminho:** O arquivo de orquestração fica em `dev/` para separar da configuração de produção.

#### Simulação de Recursos Limitados
Para garantir que a aplicação funcione corretamente sob as restrições de produção, existe o serviço `civitas-api-dev-limited` no arquivo `dev/docker-compose.yml`.
- **Objetivo:** Simular limites de CPU e Memória (ex: 0.5 CPU, 2G RAM) para evitar bugs que só ocorrem em produção devido à escassez de recursos.
- **Como ajustar:** Edite a seção `deploy.resources` no serviço `civitas-api-dev-limited` dentro do arquivo compose.
- **Como usar:** `docker-compose -f dev/docker-compose.yml up civitas-api-dev-limited`

## Configuração e Variáveis de Ambiente

A aplicação utiliza o **Infisical** para gerenciamento de segredos.

### Arquivo .env
No ambiente local, o arquivo `.env` deve conter apenas as variáveis essenciais para conectar ao Infisical e definir o ambiente:

1. `INFISICAL_TOKEN`
2. `INFISICAL_ADDRESS`
3. `ENVIRONMENT` (ex: `dev`)

### Sobrescrita de Variáveis
As demais variáveis são carregadas automaticamente do Infisical. Caso precise testar um valor diferente localmente, basta adicionar a variável no seu arquivo `.env`.
**Regra de prioridade:** O valor no `.env` local tem prioridade sobre o valor vindo do Infisical.

### Arquivos de Configuração (Python)
O carregamento das configurações no código segue o ambiente:
- **Dev** (`ENVIRONMENT=dev`): Carrega `app/config/dev.py`.
- **Staging / Produção**: Carrega `app/config/prod.py`.

## Como Executar (Dev)

1. **Configurar variáveis de ambiente**
   Copie o exemplo e ajuste conforme necessário:
   ```bash
   cp .env.example .env
   ```

2. **Subir os serviços**
   Utilize o compose específico de desenvolvimento:
   ```bash
   docker-compose -f dev/docker-compose.yml up -d --build
   ```

3. **Acessar**
   - **API Principal:** [http://localhost:8080](http://localhost:8080)
   - **API com Limite de Recursos:** [http://localhost:8081](http://localhost:8081)
   - **Documentação (Swagger):** [http://localhost:8080/docs](http://localhost:8080/docs)

## Migrations

As migrations do banco de dados são feitas com **Aerich** (Tortoise ORM). A configuração fica em `pyproject.toml` (`[tool.aerich]`) e os arquivos em `migrations/`.

São dois passos distintos: **criar** o arquivo de migration e **aplicar** as migrations no banco. O `aerich upgrade` (no Docker ou manual) **só aplica** migrations que já existem em `migrations/`; ele **não cria** novos arquivos.

**1. Criar uma nova migration (após alterar `app/models.py`)**

Você precisa rodar manualmente. Se estiver usando o banco do Docker, use um run pontual no container para que o Aerich use o mesmo ambiente (Postgres do compose):

```bash
docker compose -f dev/docker-compose.yml run --rm civitas-api-dev poetry run aerich migrate --name "descrição_da_alteração"
```

Se rodar a API fora do container (com o banco já acessível), use na sua máquina:

```bash
poetry run aerich migrate --name "descrição_da_alteração"
```

Isso gera um novo arquivo em `migrations/app/`. Revise o arquivo e faça o commit. Só depois disso a migration poderá ser aplicada.

**2. Aplicar as migrations no banco**

- **Com Docker:** O comando do serviço no `dev/docker-compose.yml` já executa `aerich upgrade` antes do uvicorn. Na subida dos containers, todas as migrations existentes em `migrations/` são aplicadas no banco. Nenhuma migration nova é criada nesse momento.
- **Sem Docker:** Rode `poetry run aerich upgrade` para aplicar as migrations pendentes.

Resumo: criar tabela ou alterar model → rodar `aerich migrate` → commitar o arquivo gerado → na próxima subida (ou ao rodar `aerich upgrade`), a migration será aplicada.

## URLs dos Ambientes

- **Staging:** `https://staging.api.civitas.rio`
- **Produção:** `https://api.civitas.rio`

## Autenticação (Authentik)

A API utiliza **Authentik** como provedor de identidade (OIDC). A conexão é configurada via variáveis no Infisical (`OIDC_BASE_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_ISSUER_URL`, `OIDC_TOKEN_URL`, etc.). O health check da aplicação verifica a disponibilidade do Authentik.

Rotas protegidas exigem o token JWT no header `Authorization: Bearer <token>`. O token é obtido em `POST /auth/token` (credenciais do Authentik). No handler, use as dependências do FastAPI para injetar o usuário e checar permissões: `is_user`, `is_agent`, `is_admin` (e `has_cpf` quando aplicável), definidas em `app/dependencies.py`.

## Definição de rotas (router_request)

Novas rotas que exigem autenticação e auditoria devem usar o decorator **`router_request`** (`app/decorators.py`) em vez de registrar o endpoint diretamente no router. Esse decorator:

- Registra a rota no router (GET, POST, etc.) com path, `response_model` e `responses`.
- Aplica **rate limit** (configurável em `config.RATE_LIMIT_DEFAULT`).
- Garante que o handler receba **`user`** e **`request`** por injeção de dependência (obrigatórios).
- Registra a requisição em **UserHistory** (auditoria) e, para rotas em `/pdf/`, em **ReportHistory**.

Exemplo:

```python
from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from fastapi import Request
from typing import Annotated
from fastapi import Depends

@router_request(method="GET", router=router, path="", response_model=None)
async def get_cameras_list(
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await get_cameras()
```

O handler deve declarar explicitamente `user` e `request` (por exemplo com `Depends(is_user)` e `Request`) para que o decorator funcione corretamente.

## Fluxo de Desenvolvimento e Contribuição

### Branching Model e CI/CD
Utilizamos um fluxo focado em integração contínua segura, onde `staging` funciona como réplica de produção para testes.

1. **Desenvolvimento**:
   - Crie uma branch a partir de `main` (ou da última versão estável).
   - Desenvolva utilizando **Feature Flags** se a mudança for grande ou contínua.

2. **Teste em Staging**:
   - Abra um PR da sua branch para `staging`.
   - O ambiente de staging é isolado (banco e serviços separados de prod).
   - Valide as alterações.

3. **Deploy em Produção (Main)**:
   - O fluxo de deploy é **Merge Staging -> Main**.
   - Se sua feature foi validada e está pronta: remova a feature flag (ou ative-a por padrão) e garanta que está tudo certo em staging.
   - Se sua feature **não** está pronta ou tem bugs: mantenha a feature flag desativada. Como o fluxo leva todo o conteúdo de staging para main, seu código incompleto irá para produção, mas ficará inativo graças à flag.
   - Isso permite que o trabalho de múltiplos desenvolvedores seja integrado em main, onde apenas o que está pronto e validado é ativado para o usuário final.

### Feature Flags
Essenciais para permitir o deploy de código em desenvolvimento sem quebrar a produção.

- **Uso:** Para grandes mudanças, refatorações ou novas features que levam tempo.
- **Implementação:** Crie uma variável de configuração (ex: `USE_NEW_SERVICE`) no `app/config/`.
- **Produção:** Mantenha `False` por padrão ou controle via variável de ambiente até a validação final.
- **Limpeza:** Após a feature estar estável em produção, remova a flag e o código antigo (refactor).

Alterações pequenas e rápidas não necessitam de feature flags.

### Commits
Seguimos o padrão **Conventional Commits**:
- `feat`: nova funcionalidade
- `fix`: correção de bug
- `chore`: tarefas de manutenção (config, build, deps)
- `refactor`: mudança de código sem alteração de comportamento
- `docs`: documentação

Exemplo:
```text
feat(cameras): add new BigQuery source for cameras
```
