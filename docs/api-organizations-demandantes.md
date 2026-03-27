# API — Organizações e demandantes

Documentação prática para integração no **front-end**: rotas REST, exemplos em `curl` e formato dos payloads.

**Prefixos**

| Recurso       | Caminho base        |
|---------------|---------------------|
| Organizações  | `/organizations`    |
| Demandantes   | `/demandants`      |

**Autenticação:** todas as rotas abaixo exigem header `Authorization: Bearer <access_token>`.

---

## Sumário

1. [Autenticação](#autenticação)
2. [Organizações](#organizações)
3. [Demandantes](#demandantes)
4. [Referência rápida](#referência-rápida)
5. [Observações](#observações)

---

## Autenticação

O token é obtido via OAuth2 *password* (form url-encoded), mesmo fluxo usado pelo Swagger.

### Obter o token

```bash
curl -s -X POST "${BASE_URL}/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=SEU_USUARIO_OU_EMAIL" \
  -d "password=SUA_SENHA"
```

A resposta inclui `access_token` e `token_type` (normalmente `bearer`).

### Variáveis úteis (copiar e colar nos exemplos)

```bash
export BASE_URL="http://localhost:8080"   # ajustar por ambiente
export TOKEN="<cole_o_access_token_aqui>"

export ORG_ID="00000000-0000-0000-0000-000000000001"
export DEM_ID="00000000-0000-0000-0000-000000000002"
```

---

## Organizações

### Listar (paginado)

Query: `page`, `size`.

```bash
curl -s "${BASE_URL}/organizations?page=1&size=50" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

### Criar

**Body (JSON):** `name`, `organization_type`, `acronym`, `jurisdiction_level` (todos obrigatórios).

```bash
curl -s -X POST "${BASE_URL}/organizations" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "12ª DP",
    "organization_type": "delegacia",
    "acronym": "12DP",
    "jurisdiction_level": "municipal"
  }'
```

### Obter por ID

```bash
curl -s "${BASE_URL}/organizations/${ORG_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

### Atualizar (parcial)

Envie apenas os campos que devem mudar.

```bash
curl -s -X PUT "${BASE_URL}/organizations/${ORG_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "12ª Delegacia de Polícia",
    "acronym": "12ª DP"
  }'
```

### Excluir

```bash
curl -s -X DELETE "${BASE_URL}/organizations/${ORG_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

> **Atenção:** em cascata no banco, remover uma organização pode remover demandantes vinculados e, por consequência, vínculos com placas monitoradas. Validar regra de negócio antes de usar em produção.

---

## Demandantes

### Listar (paginado)

Query: `page`, `size`. Opcional: `organization_id` (UUID) para filtrar.

```bash
curl -s "${BASE_URL}/demandants?page=1&size=50" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

**Filtrar por organização:**

```bash
curl -s "${BASE_URL}/demandants?organization_id=${ORG_ID}&page=1&size=50" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

### Criar

**Body (JSON):** `organization_id` obrigatório; `name`, `email`, `phone_1`, `phone_2`, `phone_3` opcionais.

```bash
curl -s -X POST "${BASE_URL}/demandants" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "'"${ORG_ID}"'",
    "name": "Gabriel Silva",
    "email": "gabriel@example.com",
    "phone_1": "21999990001",
    "phone_2": "21999990002",
    "phone_3": null
  }'
```

### Obter por ID

```bash
curl -s "${BASE_URL}/demandants/${DEM_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

### Atualizar (parcial)

```bash
curl -s -X PUT "${BASE_URL}/demandants/${DEM_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gabriel S.",
    "phone_1": "21988887777",
    "organization_id": "'"${ORG_ID}"'"
  }'
```

### Excluir

A resposta devolve o objeto do demandante **antes** da exclusão. No banco, vínculos `monitoredplate_demandant` são removidos em cascata.

```bash
curl -s -X DELETE "${BASE_URL}/demandants/${DEM_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

---

## Referência rápida

| Recurso         | Método | Path                               | Query / body                    |
|-----------------|--------|------------------------------------|---------------------------------|
| Organizações    | GET    | `/organizations`                  | `page`, `size`                  |
| Organizações    | POST   | `/organizations`                  | JSON (ver acima)                |
| Organizações    | GET    | `/organizations/{organization_id}` | —                               |
| Organizações    | PUT    | `/organizations/{organization_id}` | JSON parcial                    |
| Organizações    | DELETE | `/organizations/{organization_id}` | —                               |
| Demandantes     | GET    | `/demandants`                     | `page`, `size`, `organization_id` (opc.) |
| Demandantes     | POST   | `/demandants`                     | JSON (ver acima)                |
| Demandantes     | GET    | `/demandants/{demandant_id}`      | —                               |
| Demandantes     | PUT    | `/demandants/{demandant_id}`      | JSON parcial                    |
| Demandantes     | DELETE | `/demandants/{demandant_id}`      | —                               |

**Resposta de demandante:** inclui objeto `organization` aninhado (mesmo shape de organização nas respostas).

---

## Observações

- **OpenAPI / Swagger:** com a API no ar, acesse `{BASE_URL}/docs` para testar interativo e ver schemas exatos.
- **Paginação:** usa [fastapi-pagination](https://github.com/uriyyo/fastapi-pagination); estrutura da página (`items`, `total`, etc.) pode ser conferida na primeira resposta real ou no Swagger.
- **Atualização parcial:** no `PUT`, campos omitidos ou enviados como `null` costumam **não** sobrescrever valores existentes (comportamento alinhado ao CRUD de organizações). Para “limpar” um campo opcional, pode ser necessário evoluir a API — alinhar com o backend se surgir esse caso.
- **Rate limit:** as rotas passam pelo limiter da aplicação; em caso de `429`, respeitar `Retry-After` ou backoff se existir na resposta.

---

*Gerado para facilitar a implementação no front-end. Ajuste `BASE_URL`, credenciais e UUIDs conforme o ambiente (local, staging, produção).*
