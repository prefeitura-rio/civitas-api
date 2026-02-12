# Civitas API

API para o APP CIVITAS.

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

## URLs dos Ambientes

- **Staging:** `https://staging.api.civitas.rio`
- **Produção:** `https://api.civitas.rio`

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
