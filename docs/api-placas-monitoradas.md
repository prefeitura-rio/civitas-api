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
6. [Víncios placa–demandante (pós-cadastro)](#víncios-placa--demandante-pós-cadastro)
7. [Excluir placa monitorada](#excluir-placa-monitorada)
8. [Formato da resposta (`MonitoredPlateOut`)](#formato-da-resposta-monitoredplateout)
9. [Erros comuns](#erros-comuns)
10. [Contrato `PUT` vs rotas de víncio](#contrato-put-vs-rotas-de-víncio)

---

## Variáveis de ambiente

```bash
export BASE_URL="http://localhost:8080"
export TOKEN="<access_token>"

# Exemplos (ajustar aos UUIDs reais)
export PLACA="ABC1D23"
export ORG_ID="00000000-0000-0000-0000-000000000001"
export DEMANDANT_ID="00000000-0000-0000-0000-000000000002"
export CHANNEL_ID="00000000-0000-0000-0000-000000000003"
export LPR_EQUIPMENT_ID="00000000-0000-0000-0000-0000000000ab"
export LINK_ID="00000000-0000-0000-0000-00000000cafe"  # id do víncio em demandant_links[].id
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
| `numero_controle` | sim | Identificador interno; **único** no sistema |
| `notes` | não | Observações |
| `notification_channels` | não | Lista de UUIDs de canais de notificação |
| `demandant_links` | não | Lista de víncios placa ↔ demandante (ver abaixo) |

### Cada item de `demandant_links` — `MonitoredPlateDemandantLinkIn`

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `demandant_id` | sim | UUID do demandante (**deve existir** — cadastre antes via `/demandants`) |
| `reference_number` | sim | Número de referência interno (máx. 50 caracteres) |
| `valid_until` | não | Data/hora de validade **desse vínculo** (não é global na placa) |
| `notes` | não | Notas do víncio |
| `additional_info` | não | Objeto JSON livre |
| `lpr_equipment_ids` | não | Lista de UUIDs de equipamentos LPR; cada um vira registro em `monitoredplate_demandant_radar` |

> No cadastro, o víncio placa–demandante é criado com **`active: true`** por padrão (esse campo **não** entra no JSON do `POST`; só aparece nas respostas).

### Exemplo mínimo (sem demandantes)

```bash
curl -s -X POST "${BASE_URL}/cars/monitored" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "plate": "ABC1D23",
    "numero_controle": "CTRL-2026-0001",
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
    "numero_controle": "CTRL-2026-0001",
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
- Já existe registro com o mesmo `numero_controle`.

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
| `numero_controle` | Novo número de controle (**único**); opcional |
| `notes` | Notas; opcional |
| `notification_channels` | Lista completa de UUIDs de canais — **substitui** a lista anterior (limpa e recria associações) |

```bash
curl -s -X PUT "${BASE_URL}/cars/monitored/${PLACA}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "numero_controle": "CTRL-2026-0002",
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

## Víncios placa–demandante (pós-cadastro)

Use estas rotas para **adicionar**, **alterar** (incluindo `valid_until`, referência, notas e lista de LPR) ou **remover** um víncio depois que a placa já existe. Todas retornam a placa completa (`MonitoredPlateOut`), como o `GET` da placa.

O `link_id` é o campo `id` de cada item em `demandant_links` na resposta da API.

### Criar um novo víncio

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

### Atualizar um víncio (parcial)

**`PATCH /cars/monitored/{plate}/demandant-links/{link_id}`**

Body (`MonitoredPlateDemandantLinkPatch`): envie **apenas** os campos que devem mudar.

| Campo | Efeito |
|-------|--------|
| `reference_number` | Atualiza (não pode ser string vazia) |
| `valid_until` | Atualiza data/hora de validade do víncio |
| `active` | Ativa/desativa o víncio |
| `notes` | Atualiza notas |
| `additional_info` | Atualiza JSON |
| `lpr_equipment_ids` | Se **presente** no JSON, **substitui por completo** a lista de equipamentos LPR desse víncio (remove os que sumiram da lista e adiciona os novos) |

**Exemplo:** só mudar a validade:

```bash
curl -s -X PATCH "${BASE_URL}/cars/monitored/${PLACA}/demandant-links/${LINK_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "valid_until": "2027-01-15T12:00:00"
  }'
```

**Exemplo:** desativar víncio e trocar referência:

```bash
curl -s -X PATCH "${BASE_URL}/cars/monitored/${PLACA}/demandant-links/${LINK_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "active": false,
    "reference_number": "REF-ATUALIZADO"
  }'
```

### Remover um víncio

**`DELETE /cars/monitored/{plate}/demandant-links/{link_id}`**

A placa continua existindo; só o víncio (e radares associados a ele) é removido.

```bash
curl -s -X DELETE "${BASE_URL}/cars/monitored/${PLACA}/demandant-links/${LINK_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

---

## Excluir placa monitorada

**`DELETE /cars/monitored/{plate}`**

Remove a placa. Víncios com demandantes e radares associados a essa placa são tratados pelo banco conforme as regras de integridade (CASCADE nos víncios dependentes da placa).

```bash
curl -s -X DELETE "${BASE_URL}/cars/monitored/${PLACA}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json"
```

---

## Formato da resposta (`MonitoredPlateOut`)

Objeto principal:

- `id`, `plate`, `numero_controle`, `notes`, `created_at`, `updated_at`
- `notification_channels`: lista de canais (ids, tipo, parâmetros, etc.)
- `demandant_links`: lista de víncios, cada um com:
  - `id`, `reference_number`, `valid_until`, `active`, `notes`, `additional_info`, `created_at`, `updated_at`
  - `demandant`: objeto completo do demandante, incluindo **`organization`** aninhada
  - `radars`: lista de `{ id, lpr_equipment_id, active, ... }`

---

## Erros comuns

| Código | Situação típica |
|--------|------------------|
| `401` | Token ausente, inválido ou usuário sem permissão no app |
| `404` | Placa não encontrada; canal ou demandante inexistente no `POST` da placa; víncio (`link_id`) inexistente ou não pertence à placa |
| `409` | `plate` ou `numero_controle` duplicado no `POST`/`PUT` da placa; demandante já vinculado na mesma placa (`POST` de víncio) |
| `422` | Body inválido (ex.: formato de placa) |
| `429` | Rate limit |

---

## Contrato `PUT` vs rotas de víncio

- **`PUT /cars/monitored/{plate}`** continua servindo só para **dados da placa** (`plate`, `numero_controle`, `notes`) e **lista de canais** (`notification_channels`). **Não** inclui `demandant_links`.
- Para **criar / editar / remover** víncios depois do cadastro inicial, use:
  - `POST /cars/monitored/{plate}/demandant-links`
  - `PATCH /cars/monitored/{plate}/demandant-links/{link_id}`
  - `DELETE /cars/monitored/{plate}/demandant-links/{link_id}`

No `PATCH`, apenas campos **enviados** no JSON são aplicados (**atualização parcial**), exceto `lpr_equipment_ids`: se o campo vier no body, a lista de LPR é **substituída integralmente** pela lista enviada.

No `PUT` da placa, campos omitidos ou `null` costumam **não** sobrescrever valores já salvos (mesmo padrão de outros CRUDs do projeto).

---

## Referência rápida

| Método | Path | Uso |
|--------|------|-----|
| GET | `/cars/monitored` | Lista paginada + filtros |
| GET | `/cars/monitored/{plate}` | Detalhe |
| POST | `/cars/monitored` | Cria placa + víncios + radares |
| PUT | `/cars/monitored/{plate}` | Edita placa, `numero_controle`, notas e canais |
| POST | `/cars/monitored/{plate}/demandant-links` | Adiciona víncio placa–demandante (+ LPR opcional) |
| PATCH | `/cars/monitored/{plate}/demandant-links/{link_id}` | Atualiza víncio (parcial; LPR substitui lista se enviado) |
| DELETE | `/cars/monitored/{plate}/demandant-links/{link_id}` | Remove víncio |
| DELETE | `/cars/monitored/{plate}` | Remove placa |

**OpenAPI:** `{BASE_URL}/docs` para schemas exatos e testes interativos.

---

*Complementa o arquivo `docs/api-organizations-demandantes.md` (cadastro de organizações e demandantes usados nos víncios).*
