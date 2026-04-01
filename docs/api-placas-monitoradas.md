# API — Placas monitoradas

Guia para o **front-end**: listagem, criação, edição e leitura de placas monitoradas, incluindo vínculos com **demandantes**, **validade por vínculo** e **equipamentos LPR** (radares).

**Prefixo:** `/cars`
**Autenticação:** `Authorization: Bearer <access_token>` em todas as rotas (mesmo fluxo de `/auth/token` descrito no doc de organizações/demandantes).

---

## Sumário

1. [Variáveis de ambiente](#variáveis-de-ambiente)
2. [Listar placas monitoradas](#listar-placas-monitoradas)
3. [Obter uma placa](#obter-uma-placa)
4. [Criar placa monitorada](#criar-placa-monitorada)
5. [Editar placa monitorada](#editar-placa-monitorada)
6. [Vínculos placa–demandante (pós-cadastro)](#vínculos-placa--demandante-pós-cadastro)
7. [Excluir placa monitorada](#excluir-placa-monitorada)
8. [Formato da resposta (`MonitoredPlateOut`)](#formato-da-resposta-monitoredplateout)
9. [Erros comuns](#erros-comuns)
10. [Contrato `PUT` vs rotas de vínculo](#contrato-put-vs-rotas-de-vínculo)
11. [Job de validade (cron) e Discord](#job-de-validade-cron-e-discord)

---

## Variáveis de ambiente

```bash
export BASE_URL="http://localhost:8080"
export TOKEN="<access_token>"

# Exemplos (UUIDs onde a API exige UUID; id LPR é string do fornecedor, até 64 chars)
export PLACA="ABC1D23"
export ORG_ID="00000000-0000-0000-0000-000000000001"
export DEMANDANT_ID="00000000-0000-0000-0000-000000000002"
export CHANNEL_ID="00000000-0000-0000-0000-000000000003"
export LPR_EQUIPMENT_ID="0580041113"
export LINK_ID="00000000-0000-0000-0000-00000000cafe"  # id do vínculo em demandant_links[].id
```

---

## Listar placas monitoradas

**`GET /cars/monitored`**

Paginação padrão do projeto: `page`, `size`.

Filtros opcionais (query string):

| Parâmetro | Tipo | Descrição |
|-----------|------|------------|
| `organization_id` | UUID | Placas que tenham ao menos um vínculo com demandante dessa organização |
| `organization_name` | string | Busca parcial (`icontains`) no nome da organização do demandante |
| `demandant_link_active` | boolean | Filtra pelo flag `active` do vínculo placa–demandante |
| `notification_channel_id` | UUID | Placas associadas a esse canal |
| `notification_channel_title` | string | Busca parcial no título do canal |
| `plate_contains` | string | Busca parcial na placa |
| `start_time_create` | datetime | Início do intervalo de `created_at` |
| `end_time_create` | datetime | Fim do intervalo de `created_at` |

```bash
curl -s "${BASE_URL}/cars/monitored?page=1&size=50" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

**Exemplo:** filtrar por organização e vínculo ativo.

```bash
curl -s -G "${BASE_URL}/cars/monitored" \
  --data-urlencode "page=1" \
  --data-urlencode "size=50" \
  --data-urlencode "organization_id=${ORG_ID}" \
  --data-urlencode "demandant_link_active=true" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

---

## Obter uma placa

**`GET /cars/monitored/{plate}`**

`{plate}` é o valor da placa (7 caracteres, formato Mercosul já validado na API; na prática pode enviar em maiúsculas).

```bash
curl -s "${BASE_URL}/cars/monitored/${PLACA}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

---

## Criar placa monitorada

**`POST /cars/monitored`**

### Corpo (JSON) — `MonitoredPlateIn`

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `plate` | sim | Placa (7 caracteres; API normaliza para maiúsculas) |
| `notes` | não | Observações |
| `notification_channels` | não | Lista de UUIDs de canais de notificação |
| `demandant_links` | não | Lista de vínculos placa ↔ demandante (ver abaixo) |

### Cada item de `demandant_links` — `MonitoredPlateDemandantLinkIn`

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `demandant_id` | sim | UUID do demandante (**deve existir** — cadastre antes via `/demandants`) |
| `reference_number` | sim | Número de referência interno (máx. 50 caracteres) |
| `valid_until` | não | Data/hora de validade **desse vínculo** (não é global na placa) |
| `notes` | não | Notas do vínculo |
| `additional_info` | não | Objeto JSON livre |
| `lpr_equipment_ids` | não | Lista de identificadores de equipamento LPR (string, máx. 64 caracteres, ex.: código no BigQuery); cada um vira registro em `monitoredplate_demandant_radar` |

> No cadastro, o vínculo placa–demandante é criado com **`active: true`** por padrão (esse campo **não** entra no JSON do `POST`; só aparece nas respostas).

### Exemplo mínimo (sem demandantes)

```bash
curl -s -X POST "${BASE_URL}/cars/monitored" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "plate": "ABC1D23",
    "notes": "Exemplo"
  }'
```

### Exemplo completo (canais + dois demandantes + LPR)

```bash
curl -s -X POST "${BASE_URL}/cars/monitored" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "plate": "ABC1D23",
    "notes": "Monitoramento compartilhado",
    "notification_channels": [
      "'"${CHANNEL_ID}"'"
    ],
    "demandant_links": [
      {
        "demandant_id": "'"${DEMANDANT_ID}"'",
        "reference_number": "REF-12DP-001",
        "valid_until": "2026-12-31T23:59:59",
        "notes": "Demanda 12ª DP",
        "additional_info": { "processo": "12345" },
        "lpr_equipment_ids": [
          "'"${LPR_EQUIPMENT_ID}"'"
        ]
      }
    ]
  }'
```

### Conflitos (`409`)

- Já existe placa com o mesmo `plate`.

### Outros erros

- `404` se algum `demandant_id` ou `notification_channels` não existir.

---

## Editar placa monitorada

**`PUT /cars/monitored/{plate}`**

### Corpo (JSON) — `MonitoredPlateUpdate`

Apenas campos da entidade **placa** e **canais**. Envie só o que deve mudar.

| Campo | Descrição |
|-------|-----------|
| `plate` | Nova placa (mesmas regras de validação); opcional |
| `notes` | Notas; opcional |
| `notification_channels` | Lista completa de UUIDs de canais — **substitui** a lista anterior (limpa e recria associações) |

```bash
curl -s -X PUT "${BASE_URL}/cars/monitored/${PLACA}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Atualizado pelo painel"
  }'
```

**Atualizar só canais (lista final desejada):**

```bash
curl -s -X PUT "${BASE_URL}/cars/monitored/${PLACA}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_channels": [
      "'"${CHANNEL_ID}"'"
    ]
  }'
```

---

## Vínculos placa–demandante (pós-cadastro)

Use estas rotas para **adicionar**, **alterar** (incluindo `valid_until`, referência, notas e lista de LPR) ou **remover** um vínculo depois que a placa já existe. Todas retornam a placa completa (`MonitoredPlateOut`), como o `GET` da placa.

O `link_id` é o campo `id` de cada item em `demandant_links` na resposta da API.

### Criar um novo vínculo

**`POST /cars/monitored/{plate}/demandant-links`**

Body: mesmo formato de cada item de `demandant_links` no `POST /cars/monitored` (`MonitoredPlateDemandantLinkIn`): `demandant_id`, `reference_number`, e opcionalmente `valid_until`, `notes`, `additional_info`, `lpr_equipment_ids`.

- `409` se o mesmo `demandant_id` já estiver ligado a esta placa.

```bash
curl -s -X POST "${BASE_URL}/cars/monitored/${PLACA}/demandant-links" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "demandant_id": "'"${DEMANDANT_ID}"'",
    "reference_number": "REF-NOVO-001",
    "valid_until": "2026-06-30T23:59:59",
    "notes": "Inclusão posterior",
    "lpr_equipment_ids": [
      "'"${LPR_EQUIPMENT_ID}"'"
    ]
  }'
```

### Atualizar um vínculo (parcial)

**`PATCH /cars/monitored/{plate}/demandant-links/{link_id}`**

Body (`MonitoredPlateDemandantLinkPatch`): envie **apenas** os campos que devem mudar.

| Campo | Efeito |
|-------|--------|
| `reference_number` | Atualiza (não pode ser string vazia) |
| `valid_until` | Atualiza data/hora de validade do vínculo |
| `active` | Ativa/desativa o vínculo |
| `notes` | Atualiza notas |
| `additional_info` | Atualiza JSON |
| `lpr_equipment_ids` | Se **presente** no JSON, **substitui por completo** a lista de equipamentos LPR desse vínculo (remove os que sumiram da lista e adiciona os novos) |

**Exemplo:** só mudar a validade:

```bash
curl -s -X PATCH "${BASE_URL}/cars/monitored/${PLACA}/demandant-links/${LINK_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "valid_until": "2027-01-15T12:00:00"
  }'
```

**Exemplo:** desativar vínculo e trocar referência:

```bash
curl -s -X PATCH "${BASE_URL}/cars/monitored/${PLACA}/demandant-links/${LINK_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "active": false,
    "reference_number": "REF-ATUALIZADO"
  }'
```

### Remover um vínculo

**`DELETE /cars/monitored/{plate}/demandant-links/{link_id}`**

A placa continua existindo; só o vínculo (e radares associados a ele) é removido.

```bash
curl -s -X DELETE "${BASE_URL}/cars/monitored/${PLACA}/demandant-links/${LINK_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

---

## Excluir placa monitorada

**`DELETE /cars/monitored/{plate}`**

Remove a placa. Vínculos com demandantes e radares associados a essa placa são tratados pelo banco conforme as regras de integridade (CASCADE nos vínculos dependentes da placa).

```bash
curl -s -X DELETE "${BASE_URL}/cars/monitored/${PLACA}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

---

## Formato da resposta (`MonitoredPlateOut`)

Objeto principal:

- `id`, `plate`, `notes`, `created_at`, `updated_at`
- `notification_channels`: lista de canais (ids, tipo, parâmetros, etc.)
- `demandant_links`: lista de vínculos, cada um com:
  - `id`, `reference_number`, `valid_until`, `active`, `validity_warning_sent_at` (opcional; job de 7 dias), `notes`, `additional_info`, `created_at`, `updated_at`
  - `demandant`: objeto completo do demandante, incluindo **`organization`** aninhada
  - `radars`: lista de `{ id, lpr_equipment_id, active, ... }`

---

## Erros comuns

| Código | Situação típica |
|--------|------------------|
| `401` | Token ausente, inválido ou usuário sem permissão no app |
| `404` | Placa não encontrada; canal ou demandante inexistente no `POST` da placa; vínculo (`link_id`) inexistente ou não pertence à placa |
| `409` | `plate` duplicada no `POST` da placa; demandante já vinculado na mesma placa (`POST` de vínculo) |
| `422` | Body inválido (ex.: formato de placa) |
| `429` | Rate limit |

---

## Contrato `PUT` vs rotas de vínculo

- **`PUT /cars/monitored/{plate}`** continua servindo só para **dados da placa** (`plate`, `notes`) e **lista de canais** (`notification_channels`). **Não** inclui `demandant_links`.
- Para **criar / editar / remover** vínculos depois do cadastro inicial, use:
  - `POST /cars/monitored/{plate}/demandant-links`
  - `PATCH /cars/monitored/{plate}/demandant-links/{link_id}`
  - `DELETE /cars/monitored/{plate}/demandant-links/{link_id}`

No `PATCH`, apenas campos **enviados** no JSON são aplicados (**atualização parcial**), exceto `lpr_equipment_ids`: se o campo vier no body, a lista de LPR é **substituída integralmente** pela lista enviada.

No `PUT` da placa, campos omitidos ou `null` costumam **não** sobrescrever valores já salvos (mesmo padrão de outros CRUDs do projeto).

---

## Job de validade (cron) e Discord

Um script em segundo plano aplica regras de **`valid_until`** nos vínculos e pode postar nos webhooks Discord **associados à placa** (`notification_channels` do tipo `discord`):

1. **Expiração:** se `valid_until` não é nulo e já passou (fuso `America/Sao_Paulo` da API), o vínculo passa a `active: false` e é enviada mensagem de expiração ao Discord.
2. **Aviso 7 dias:** na **data** que cai exatamente **7 dias antes** da data de `valid_until`, envia um aviso **uma vez** (campo `validity_warning_sent_at` no vínculo). Só ocorre se o intervalo (**`updated_at` → `valid_until`**) for **≥ 7 dias** — assim, se o operador alterar o vínculo (incluindo prorrogar ou encurtar `valid_until`), a elegibilidade reflete a última atualização; se `updated_at` for nulo (legado), usa-se `created_at`. Ao mudar `valid_until` via `PATCH`, `validity_warning_sent_at` é **zerado** para permitir um novo aviso para a nova data.

**Executar (após migrar o banco):**

```bash
poetry run aerich upgrade
poetry run python scripts/run_validity_jobs.py
```

**Operação:** agende o comando acima (cron ou Kubernetes `CronJob`), idealmente **1× por dia** para o aviso de 7 dias; pode rodar com maior frequência só para expirações mais próximas do minuto.

**Lock Redis:** por padrão o script usa a chave `civitas:validity_job_lock` para evitar corrida entre réplicas. Em ambiente sem Redis ou para teste local: `VALIDITY_JOB_SKIP_LOCK=true`.

**Resposta da API:** cada item em `demandant_links` pode incluir `validity_warning_sent_at` após o primeiro aviso enviado com sucesso.

**Testes automatizados (SQLite em memória, sem Infisical):**

```bash
poetry run pytest tests/test_monitored_plate_validity.py -v
```

---

## Referência rápida

| Método | Path | Uso |
|--------|------|-----|
| GET | `/cars/monitored` | Lista paginada + filtros |
| GET | `/cars/monitored/{plate}` | Detalhe |
| POST | `/cars/monitored` | Cria placa + vínculos + radares |
| PUT | `/cars/monitored/{plate}` | Edita placa (`plate`), notas e canais |
| POST | `/cars/monitored/{plate}/demandant-links` | Adiciona vínculo placa–demandante (+ LPR opcional) |
| PATCH | `/cars/monitored/{plate}/demandant-links/{link_id}` | Atualiza vínculo (parcial; LPR substitui lista se enviado) |
| DELETE | `/cars/monitored/{plate}/demandant-links/{link_id}` | Remove vínculo |
| DELETE | `/cars/monitored/{plate}` | Remove placa |

**OpenAPI:** `{BASE_URL}/docs` para schemas exatos e testes interativos.

---

*Complementa o arquivo `docs/api-organizations-demandantes.md` (cadastro de organizações e demandantes usados nos vínculos).*
