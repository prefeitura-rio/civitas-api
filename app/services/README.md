# Service Layer

Este diretório contém a camada de serviços da aplicação CIVITAS API, implementando o padrão de Service Layer para encapsular a lógica de negócio e promover separação de responsabilidades.

## Estrutura

```
app/services/
├── __init__.py                    # Exports dos services
├── cortex_service.py             # Interações com API Cortex
├── plate_service.py              # Lógica de negócio de placas
├── bigquery_service.py           # Operações BigQuery
├── monitored_plate_service.py    # Placas monitoradas
└── README.md                     # Este arquivo
```

## Conceitos

### Service Layer Pattern

O Service Layer encapsula a lógica de negócio da aplicação, oferecendo uma interface simplificada para os controllers (routers). Os benefícios incluem:

- **Separação de responsabilidades**: Controllers focam em HTTP, Services em lógica de negócio
- **Reutilização**: Services podem ser usados por múltiplos endpoints
- **Testabilidade**: Lógica de negócio isolada e fácil de testar
- **Manutenibilidade**: Mudanças na lógica concentradas em um local

## Services Disponíveis

### CortexService

Encapsula todas as interações com a API externa Cortex.

```python
from app.services import CortexService

# Buscar dados de veículo
success, data = await CortexService.get_vehicle_data(plate="ABC1234", cpf="12345678901")

# Buscar dados de pessoa
success, data = await CortexService.get_person_data(lookup_cpf="12345678901", requester_cpf="98765432100")

# Verificar bloqueio legal
is_blocked = CortexService.is_legal_block_error(response)
```

### PlateService

Gerencia operações relacionadas a placas de veículos.

```python
from app.services import PlateService

# Buscar detalhes de uma placa (com cache)
plate_details = await PlateService.get_plate_details(plate="ABC1234", cpf="12345678901")

# Buscar múltiplas placas em lote
plates_details = await PlateService.get_multiple_plates_details(
    plates=["ABC1234", "XYZ5678"], 
    cpf="12345678901"
)

# Calcular créditos necessários
credits = await PlateService.calculate_credits_needed(["ABC1234", "XYZ5678"])
```

### BigQueryService

Encapsula consultas complexas ao BigQuery para análise de tráfego.

```python
from app.services import BigQueryService

# Buscar sugestões de placas
hints = await BigQueryService.get_vehicle_hints(
    plate="ABC", 
    start_time=start_time, 
    end_time=end_time
)

# Obter caminho do veículo
path = await BigQueryService.get_vehicle_path(
    plate="ABC1234", 
    start_time=start_time, 
    end_time=end_time
)

# Placas antes/depois
plates = await BigQueryService.get_plates_before_after(
    plate="ABC1234",
    start_time=start_time,
    end_time=end_time,
    n_minutes=30
)
```

### MonitoredPlateService

Gerencia operações CRUD de placas monitoradas.

```python
from app.services import MonitoredPlateService

# Listar placas monitoradas com filtros
plates = await MonitoredPlateService.get_monitored_plates(
    params=params,
    operation_id=operation_id,
    active=True
)

# Criar placa monitorada
plate = await MonitoredPlateService.create_monitored_plate(plate_data, user)

# Histórico de placas monitoradas
history = await MonitoredPlateService.get_monitored_plates_history(params)
```

## Como Usar nos Routers

### Antes (sem Service Layer)

```python
@router.get("/cars/plate/{plate}")
async def get_plate_details(plate: str, user: User):
    # Validação inline
    plate = plate.upper()
    if not validate_plate(plate):
        raise HTTPException(status_code=400, detail="Invalid plate format")
    
    # Lógica de negócio no controller
    plate_data = await PlateData.get_or_none(plate=plate)
    if plate_data:
        return CortexPlacaOut(**plate_data.data, ...)
    
    # Chamada API inline
    success, data = await cortex_request(...)
    if not success:
        # Tratamento de erro inline
        if isinstance(data, aiohttp.ClientResponse) and data.status == 451:
            raise HTTPException(status_code=451, detail="...")
    
    # Persistência inline
    plate_data = await PlateData.create(plate=plate, data=data)
    return CortexPlacaOut(**data, ...)
```

### Depois (com Service Layer)

```python
@router.get("/cars/plate/{plate}")
async def get_plate_details(plate: str, user: User):
    # Toda a lógica encapsulada no service
    return await PlateService.get_plate_details(plate=plate, cpf=user.cpf)
```

## Princípios de Design

### 1. Responsabilidade Única
Cada service tem uma responsabilidade específica:
- `CortexService`: APIs externas
- `PlateService`: Lógica de placas
- `BigQueryService`: Análise de dados
- `MonitoredPlateService`: Placas monitoradas

### 2. Métodos Estáticos
Services usam métodos estáticos por serem stateless e não precisarem de instanciação.

### 3. Tratamento de Erros Consistente
Services definem como tratar erros específicos do domínio, permitindo que controllers façam tratamento básico.

### 4. Reutilização
Services podem ser reutilizados entre diferentes endpoints e até mesmo em scripts/tasks.

## Testes

Services facilitam testes unitários focados:

```python
# Teste do service isoladamente
async def test_plate_service_validation():
    # Não precisa de servidor HTTP
    result = await PlateService.get_plate_details("INVALID", "12345678901", raise_for_errors=False)
    assert result is None

# Mock apenas as dependências externas
async def test_plate_service_cortex_integration():
    with patch("app.services.CortexService.get_vehicle_data") as mock_cortex:
        mock_cortex.return_value = (True, {"placa": "ABC1234"})
        result = await PlateService.get_plate_details("ABC1234", "12345678901")
        assert result.placa == "ABC1234"
```

## Migração Gradual

Para migrar do código existente:

1. **Identifique padrões**: Encontre lógica repetida nos routers
2. **Extraia para service**: Mova lógica de negócio para um service
3. **Mantenha compatibilidade**: Use tanto utils antigos quanto services novos
4. **Teste**: Garanta que funcionalidade não quebrou
5. **Remova código antigo**: Após confirmação, remova funções não usadas

## Exemplo de Migração

```python
# 1. Criar service method
class PlateService:
    @staticmethod
    async def get_plate_details(plate: str, cpf: str):
        # Lógica movida de utils.get_plate_details
        pass

# 2. Atualizar router
@router.get("/cars/plate/{plate}")
async def get_plate_details(plate: str, user: User):
    # return await utils_get_plate_details(plate=plate, cpf=user.cpf)  # Antigo
    return await PlateService.get_plate_details(plate=plate, cpf=user.cpf)  # Novo

# 3. Manter utils temporariamente para compatibilidade
# 4. Remover utils após migração completa
```

## Benefícios Alcançados

- ✅ **Código mais limpo**: Routers focam em HTTP, services em lógica
- ✅ **Melhor testabilidade**: Services testáveis independentemente
- ✅ **Reutilização**: Lógica compartilhável entre endpoints
- ✅ **Manutenibilidade**: Mudanças centralizadas
- ✅ **Separação de responsabilidades**: Cada camada tem papel definido
- ✅ **Facilita refatoração**: Services podem evoluir independentemente
