# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Dict, List, Literal, Optional
from uuid import UUID
from enum import Enum
from zlib import crc32

from fastapi import Query
from pydantic import BaseModel, Field, root_validator, validator

from app.enums import NotificationChannelTypeEnum
from app.models import MonitoredPlate


class CortexArrendatario(BaseModel):
    enderecoArrendatario: Optional[str]
    id: Optional[int]
    nomeArrendatario: Optional[str]
    numeroDocumentoArrendatario: Optional[str]
    placa: Optional[str]
    tipoDocumentoArrendatario: Optional[str]


class CortexPossuidor(BaseModel):
    enderecoPossuidor: Optional[str]
    id: Optional[int]
    nomePossuidor: Optional[str]
    numeroDocumentoPossuidor: Optional[str]
    placa: Optional[str]
    tipoDocumentoPossuidor: Optional[str]


class CortexProprietario(BaseModel):
    enderecoProprietario: Optional[str]
    id: Optional[int]
    nomeProprietario: Optional[str]
    numeroDocumentoProprietario: Optional[str]
    placa: Optional[str]
    tipoDocumentoProprietario: Optional[str]


class CortexIndiceNacionalVeiculo(BaseModel):
    id: Optional[int]
    metodo: Optional[str]
    qtd: Optional[int]


class CortexRestricao(BaseModel):
    anoBO: Optional[str]
    dataOcorrencia: Optional[datetime]
    dddContato: Optional[str]
    historico: Optional[str]
    id: Optional[int]
    municipioBO: Optional[str]
    naturezaOcorrencia: Optional[str]
    nomeDeclarante: Optional[str]
    numeroBO: Optional[str]
    placa: Optional[str]
    ramalContato: Optional[str]
    sistema: Optional[str]
    telefoneContato: Optional[str]
    ufBO: Optional[str]
    unidadePolicial: Optional[str]


class CortexPlacaOut(BaseModel):
    anoFabricacao: Optional[str]
    anoModelo: Optional[str]
    anoUltimoLicenciamnento: Optional[int]
    arrendatario: Optional[CortexArrendatario]
    capacidadeMaximaCarga: Optional[str]
    capacidadeMaximaTracao: Optional[str]
    carroceria: Optional[str]
    categoria: Optional[str]
    chassi: Optional[str]
    cilindrada: Optional[int]
    codigoCarroceira: Optional[int]
    codigoCategoria: Optional[int]
    codigoCor: Optional[int]
    codigoEspecie: Optional[int]
    codigoMarcaModelo: Optional[int]
    codigoMunicipioEmplacamento: Optional[str]
    codigoOrgaoSRF: Optional[str]
    codigoSegurancaCRV: Optional[str]
    codigoTipoVeiculo: Optional[int]
    combustivel: Optional[str]
    cor: Optional[str]
    dataAtualizacaoAlarme: Optional[str]
    dataAtualizacaoRouboFurto: Optional[str]
    dataAtualizacaoVeiculo: Optional[str]
    dataDeclaracaoImportacao: Optional[str]
    dataEmissaoCRLV: Optional[datetime]
    dataEmissaoUltimoCRV: Optional[str]
    dataEmplacamento: Optional[datetime]
    dataHoraAtualizacaoVeiculo: Optional[datetime]
    dataLimiteRestricaoTributaria: Optional[str]
    dataPreCadastro: Optional[str]
    dataReplicacao: Optional[datetime]
    descricaoOrgaoRegiaoFiscal: Optional[str]
    especie: Optional[str]
    flagAtivo: Optional[bool]
    grupoVeiculo: Optional[str]
    id: Optional[int]
    identificadorUnicoVeiculo: Optional[str]
    indicadorRemarcacaoChassi: Optional[bool]
    indicadorVeiculoLicenciadoCirculacao: Optional[str]
    indicadorVeiculoNacional: Optional[bool]
    indiceNacionalVeiculos: Optional[List[CortexIndiceNacionalVeiculo]]
    lotacao: Optional[str]
    marcaModelo: Optional[str]
    mesAnoValidadeLicenciamento: Optional[int]
    mesFabricacaoVeiculo: Optional[str]
    municipioPlaca: Optional[str]
    nomeArrendatario: Optional[str]
    nomePossuidor: Optional[str]
    nomeProprietario: Optional[str]
    numeroCRV: Optional[str]
    numeroCaixaCambio: Optional[str]
    numeroCarroceria: Optional[str]
    numeroDeclaracaoImportacao: Optional[str]
    numeroEixoAuxiliar: Optional[str]
    numeroEixoTraseiro: Optional[str]
    numeroIdentificacaoFaturado: Optional[str]
    numeroIdentificacaoImportador: Optional[str]
    numeroLicencaUsoConfiguracaoVeiculosMotor: Optional[str]
    numeroMotor: Optional[str]
    numeroProcessoImportacao: Optional[str]
    numeroSequenciaCRV: Optional[str]
    numeroTipoCRLV: Optional[str]
    numeroViaCRLV: Optional[int]
    numeroViaCRV: Optional[int]
    origemPossuidor: Optional[str]
    paisTransferenciaVeiculo: Optional[str]
    pesoBrutoTotal: Optional[str]
    placa: Optional[str]
    placaPreMercosul: Optional[str]
    possuidor: Optional[CortexPossuidor]
    potencia: Optional[int]
    proprietario: Optional[CortexProprietario]
    quantidadeEixo: Optional[str]
    quantidadeRestricoesBaseEmplacamento: Optional[str]
    registroAduaneiro: Optional[str]
    renavam: Optional[str]
    restricao: Optional[List[CortexRestricao]]
    restricaoVeiculo1: Optional[str]
    restricaoVeiculo2: Optional[str]
    restricaoVeiculo3: Optional[str]
    restricaoVeiculo4: Optional[str]
    situacaoVeiculo: Optional[str]
    tipoDocumentoFaturado: Optional[str]
    tipoDocumentoProprietario: Optional[str]
    tipoMontagem: Optional[str]
    tipoVeiculo: Optional[str]
    ufDestinoVeiculoFaturado: Optional[str]
    ufEmplacamento: Optional[str]
    ufFatura: Optional[str]
    ufJurisdicaoVeiculo: Optional[str]
    valorIPVA: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class CortexPlacasIn(BaseModel):
    plates: List[str]
    raise_for_errors: Optional[bool] = True


class CortexIndiceNacionalPessoa(BaseModel):
    id: Optional[int]
    metodo: Optional[str]
    qtd: Optional[int]


class CortexPersonOut(BaseModel):
    anoExercicioOcupacao: Optional[str]
    anoObito: Optional[str]
    bairro: Optional[str]
    cep: Optional[str]
    complementoLogradouro: Optional[str]
    dataAtualizacao: Optional[datetime]
    dataNascimento: Optional[str]
    ddd: Optional[str]
    id: Optional[int]
    identificadorResidenteExterior: Optional[str]
    indicadorEstrangeiro: Optional[str]
    indicadorMoradorEstrangeiro: Optional[bool]
    indiceNacionalPessoas: Optional[List[CortexIndiceNacionalPessoa]]
    latitudeAproximadaLocal: Optional[float]
    logradouro: Optional[str]
    longitudeAproximadaLocal: Optional[float]
    municipio: Optional[str]
    municipioNaturalidade: Optional[str]
    naturezaOcupacao: Optional[str]
    nomeCompleto: Optional[str]
    nomeMae: Optional[str]
    nomeSocial: Optional[str]
    numeroCPF: Optional[str]
    numeroLogradouro: Optional[str]
    ocupacaoPrincipal: Optional[str]
    paisNascimento: Optional[str]
    paisResidencia: Optional[str]
    regiaoFiscal: Optional[str]
    sexo: Optional[str]
    situacaoCadastral: Optional[str]
    telefone: Optional[str]
    tipoLogradouro: Optional[str]
    tituloEleitor: Optional[str]
    uf: Optional[str]
    ufNaturalidade: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class CortexPeopleIn(BaseModel):
    cpfs: List[str]


class CortexCnpjContador(BaseModel):
    classificacaoCRCContadorPF: Optional[str]
    classificacaoCRCEmpresaContabil: Optional[str]
    cnpjEmpresaContabil: Optional[str]
    crcEmpresaContabil: Optional[str]
    nomeContador: Optional[str]
    numeroCPFContador: Optional[str]
    numeroRegistroContadorPF: Optional[str]
    tipoCRCContadorPF: Optional[str]
    tipoCRCEmpresaContabil: Optional[str]
    ufCRCContador: Optional[str]
    ufCRCEmpresaContabil: Optional[str]


class CortexCnpjSocio(BaseModel):
    cpfRepresentanteLegal: Optional[str]
    dataEntradaSociedade: Optional[str]
    identificadorSocio: Optional[str]
    nomeRepresentanteLegal: Optional[str]
    nomeSocio: Optional[str]
    numeroCPF: Optional[str]
    paisSocioEstrangeiro: Optional[str]
    percentualCapitalSocial: Optional[float]
    qualificacaoRepresentanteLegal: Optional[str]
    qualificacaoSocio: Optional[str]


class CortexSucessao(BaseModel):
    cnpjSucedida: Optional[str]
    cnpjSucessora: Optional[str]
    dataOperacaoSucessora: Optional[str]
    operacaoRealizadaSucessora: Optional[str]
    razaoSocialSucedida: Optional[str]
    razaoSocialSucessora: Optional[str]


class CortexCompanyOut(BaseModel):
    bairro: Optional[str]
    capitalSocialEmpresa: Optional[str]
    cep: Optional[str]
    cnaeFiscal: Optional[str]
    cnaeSecundario: Optional[str]
    cnpj: Optional[str]
    cnpjContador: Optional[List[CortexCnpjContador]]
    cnpjSocio: Optional[List[CortexCnpjSocio]]
    codigoCnaeFiscal: Optional[str]
    codigoCnaeSecundario: Optional[str]
    complementoLogradouro: Optional[str]
    cpfResponsavel: Optional[str]
    dataExclusaoSimples: Optional[str]
    dataInicioAtividade: Optional[str]
    dataOpcaoSimples: Optional[str]
    dataSituacaoCadastral: Optional[str]
    email: Optional[str]
    fax: Optional[str]
    indicadorMatrizFilial: Optional[str]
    logradouro: Optional[str]
    motivoSituacaoCadastral: Optional[str]
    municipio: Optional[str]
    naturezaJuridica: Optional[str]
    nomeCidadeExterior: Optional[str]
    nomeFantasia: Optional[str]
    nomePais: Optional[str]
    nomeResponsavel: Optional[str]
    numeroLogradouro: Optional[str]
    opcaoSimples: Optional[str]
    porteEmpresa: Optional[str]
    qualificacaoPessoaJuridicaResponsavelEmpresa: Optional[str]
    razaoSocial: Optional[str]
    situacaoCadastral: Optional[str]
    sucessao: Optional[List[CortexSucessao]]
    telefone1: Optional[str]
    telefone2: Optional[str]
    tipoLogradouro: Optional[str]
    uf: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class CortexCompaniesIn(BaseModel):
    cnpjs: List[str]


class CortexCreditsOut(BaseModel):
    credits: int


class HealthCheck(BaseModel):
    status: str


class OIDCUser(BaseModel):
    iss: str
    sub: str
    aud: str
    exp: int
    iat: int
    auth_time: int
    acr: str
    azp: str
    uid: str
    email: Optional[str] = None
    email_verified: bool | None
    name: Optional[str] = None
    given_name: Optional[str] = None
    preferred_username: Optional[str] = None
    nickname: str
    groups: list[str]
    matricula: Optional[str] = None
    orgao: Optional[str] = None
    setor: Optional[str] = None
    cpf: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class Location(BaseModel):
    datahora: datetime
    codcet: str
    latitude: float
    longitude: float
    bairro: str
    localidade: str
    velocidade: float
    seconds_to_next_point: Optional[float] = None


class Step(BaseModel):
    distanceMeters: Optional[int] = None
    staticDuration: str
    polyline: dict
    startLocation: dict
    endLocation: dict
    navigationInstruction: Optional[dict] = None
    localizedValues: dict
    travelMode: str


class Leg(BaseModel):
    distanceMeters: Optional[int] = None
    duration: str
    staticDuration: str
    polyline: dict
    startLocation: dict
    endLocation: dict
    steps: List[Step]
    localizedValues: dict


class Route(BaseModel):
    legs: List[Leg]


class Polyline(BaseModel):
    routes: List[Route]


class LocationsItem(BaseModel):
    locations: List[List[Location]]


class PolylineItem(BaseModel):
    polyline: List[Polyline]


class Path(BaseModel):
    locations: List[List[Location]]
    polyline: Optional[List[Polyline]] = None


class AgentLocationIn(BaseModel):
    name: str
    contact_info: str
    operation: str
    latitude: float
    longitude: float


class AgentLocationOut(BaseModel):
    name: str
    contact_info: str
    operation: str
    latitude: float
    longitude: float
    last_update: datetime


class CarPassageOut(BaseModel):
    plate: str
    timestamp: datetime
    speed: float


class DataRelayResponse(BaseModel):
    success: bool
    message: str


class MonitoredPlateIn(BaseModel):
    plate: str = Field(...)
    operation_id: UUID
    active: Optional[bool] = True
    contact_info: Optional[str] = None
    notes: Optional[str] = None
    additional_info: Optional[dict] = None
    notification_channels: Optional[List[UUID]] = None

    @validator("plate")
    def validate_plate(cls, value: str):
        from app.utils import validate_plate as validate_plate_util

        # Ensure the plate is upper case
        value = value.upper()

        # Ensure the plate has the correct format
        if not validate_plate_util(value):
            raise ValueError(
                "plate must have exactly 7 characters: "
                "first 3 letters, 4th digit, 5th letter or digit, last 2 digits"
            )

        return value


class MonitoredPlateOut(BaseModel):
    id: UUID
    plate: str
    operation: Optional["OperationOut"] = None
    active: bool
    contact_info: Optional[str] = None
    notes: Optional[str] = None
    additional_info: Optional[dict] = None
    notification_channels: Optional[List["NotificationChannelOut"]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

    @classmethod
    async def from_monitored_plate(cls, monitored_plate: MonitoredPlate):
        return MonitoredPlateOut(
            id=monitored_plate.id,
            plate=monitored_plate.plate,
            operation=(
                OperationOut.from_orm(await monitored_plate.operation)
                if await monitored_plate.operation
                else None
            ),
            active=monitored_plate.active,
            contact_info=monitored_plate.contact_info,
            notes=monitored_plate.notes,
            additional_info=monitored_plate.additional_info,
            notification_channels=[
                NotificationChannelOut.from_orm(channel)
                for channel in await monitored_plate.notification_channels.all()
            ],
            created_at=monitored_plate.created_at,
            updated_at=monitored_plate.updated_at,
        )


class MonitoredPlateHistory(BaseModel):
    plate: str
    contact_info: Optional[str] = None
    notes: Optional[str] = None
    created_timestamp: Optional[datetime] = None
    created_by: Optional["UserOut"] = None
    deleted_timestamp: Optional[datetime] = None
    deleted_by: Optional["UserOut"] = None


class MonitoredPlateUpdate(BaseModel):
    plate: Optional[str] = Field(default=None)
    operation_id: Optional[UUID] = None
    active: Optional[bool] = None
    contact_info: Optional[str] = None
    notes: Optional[str] = None
    additional_info: Optional[dict] = None
    notification_channels: Optional[List[UUID]] = None

    @validator("plate")
    def validate_plate(cls, value: str):
        from app.utils import validate_plate as validate_plate_util

        if value is not None:
            # Ensure the plate is upper case
            value = value.upper()

        # Ensure the plate has the correct format
        if not validate_plate_util(value):
            raise ValueError(
                "plate must have exactly 7 characters: "
                "first 3 letters, 4th digit, 5th letter or digit, last 2 digits"
            )

        return value


class NotificationChannelIn(BaseModel):
    title: str
    channel_type: NotificationChannelTypeEnum
    parameters: dict


class NotificationChannelOut(BaseModel):
    id: UUID
    title: Optional[str] = None
    channel_type: NotificationChannelTypeEnum
    parameters: dict
    active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class NotificationChannelUpdate(BaseModel):
    title: Optional[str] = None
    active: Optional[bool] = None


class NPlatesBeforeAfterDetection(BaseModel):
    timestamp: Optional[datetime] = None
    plate: str
    codcet: str
    lane: str
    speed: Optional[float] = None
    count: Optional[int] = None


class NPlatesBeforeAfterOut(BaseModel):
    radars: List[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    detection_time: Optional[datetime] = None
    total_detections: Optional[int] = None
    detections: List[NPlatesBeforeAfterDetection] = None


class OperationIn(BaseModel):
    title: str
    description: Optional[str] = None


class OperationOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class OperationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class RadarOut(BaseModel):
    codcet: str
    latitude: float
    longitude: float
    locequip: Optional[str] = None
    bairro: Optional[str] = None
    logradouro: Optional[str] = None
    has_data: str
    empresa: Optional[str] = None
    active_in_last_24_hours: Optional[str] = None
    last_detection_time: Optional[datetime] = None
    sentido: Optional[str] = None


class ReportFilters(BaseModel):
    limit: int
    offset: int
    semantically_similar: Optional[str] = None
    id_report: Optional[str] = None
    id_report_original: Optional[str] = None
    id_source_contains: Optional[List[str]] = None
    data_report_min: Optional[datetime] = None
    data_report_max: Optional[datetime] = None
    categoria_contains: Optional[List[str]] = None
    descricao_contains: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    latitude_min: Optional[float] = None
    latitude_max: Optional[float] = None
    longitude_min: Optional[float] = None
    longitude_max: Optional[float] = None


class ReportTipoSubtipo(BaseModel):
    tipo: str
    subtipo: List[str]


class ReportAdditionalInfo(BaseModel):
    certainty: float


class ReportOut(BaseModel):
    id_report: str
    id_source: str
    id_report_original: str
    data_report: datetime
    orgaos: List[str]
    categoria: str
    tipo_subtipo: List[ReportTipoSubtipo]
    descricao: Optional[str] = None
    logradouro: Optional[str] = None
    numero_logradouro: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    updated_at: datetime
    additional_info: Optional[ReportAdditionalInfo] = None


class ReportLatLongOut(BaseModel):
    id_report: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ReportTimelineOut(BaseModel):
    data_report: datetime
    id_source: str
    count: int


class ReportTopSubtypesOut(BaseModel):
    tipo: str
    subtipo: Optional[str] = None
    count: int


class ReportsMetadata(BaseModel):
    distinct_sources: List[str]
    distinct_categories: List[str]
    distinct_types: List[str]
    type_subtypes: Dict[str, List[str]]


class UserCortexRemainingCreditOut(BaseModel):
    remaining_credit: int
    time_until_reset: int


class UserHistoryOut(BaseModel):
    id: UUID
    method: str
    path: str
    query_params: Optional[dict] = None
    body: Optional[dict] = None
    status_code: int
    timestamp: datetime


class UserOut(BaseModel):
    id: UUID
    username: str
    full_name: Optional[str] = None
    cpf: Optional[str] = None
    registration: Optional[str] = None
    agency: Optional[str] = None
    sector: Optional[str] = None
    email: Optional[str] = None
    is_admin: bool

    class Config:
        orm_mode = True


class WazeAlertOut(BaseModel):
    timestamp: datetime
    street: Optional[str] = None
    type: str
    subtype: str
    reliability: float
    confidence: float
    number_thumbs_up: Optional[int] = None
    latitude: float
    longitude: float


class PdfReportCorrelatedPlatesDataDetection(BaseModel):
    timestamp: datetime
    plate: str
    codcet: str
    lane: str
    speed: float
    count: int


class PdfReportCorrelatedPlatesData(BaseModel):
    radars: List[str]
    start_time: datetime
    end_time: datetime
    location: str
    latitude: float
    longitude: float
    detection_time: datetime
    total_detections: int
    detections: List[PdfReportCorrelatedPlatesDataDetection]


class PdfReportCorrelatedPlatesParams(BaseModel):
    plate: str
    start_time: datetime
    end_time: datetime
    n_minutes: int
    n_plates: int


class PdfReportCorrelatedPlatesRanking(BaseModel):
    plate: str
    count: int


class PdfReportCorrelatedPlatesIn(BaseModel):
    report_data: List[PdfReportCorrelatedPlatesData] = []
    params: PdfReportCorrelatedPlatesParams
    ranking: List[PdfReportCorrelatedPlatesRanking] = []


class RequestedPlateData(BaseModel):
    plate: str
    start: datetime
    end: datetime
    n_minutes: Optional[int] = None
    n_plates: Optional[int] = None
    target_id: Optional[int] = None


class VehicleType(str, Enum):
    AUTOMOVEL = 'automovel'
    CAMINHAO = 'caminhao'
    CAMINHAO_ONIBUS = 'caminhao_onibus'
    CICLOMOTOR = 'ciclomotor'
    INDEFINIDO = 'indefinido'
    MOTO = 'moto'
    ONIBUS = 'onibus'
    
    
class PdfReportMultipleCorrelatedPlatesIn(BaseModel):
    requested_plates_data: List[RequestedPlateData]
    n_minutes: int = Field(gt=0, le=20, description="Must be between 1 and 20")
    n_plates: Optional[int] = Field(gt=0, description="Must be greater than 0")
    min_different_targets: int = Field(gt=0, description="Must be greater than 0")
    # vehicle_types: List[VehicleType] = Field(
    #     default=[VehicleType.AUTOMOVEL, VehicleType.INDEFINIDO],
    #     description="Must be a list of vehicle types."
    # )
    keep_buses: bool = Field(default=False, description="Must be a boolean")
    before_after: Optional[Literal["before", "after"]]
    report_title: str = "Relatório de Identificação de Veículos"
    
    
class DetectionWindow(BaseModel):
    plate: str
    codcet: str
    detection_index: int
    target_id: int
    n_minutes: int
    n_plates: Optional[int] = None
    start_time: datetime
    end_time: datetime
    local_detection_datetime: datetime
    start_window: datetime
    end_window: datetime
    
class DetectionWindowList(BaseModel):
    detection_window_list: List[DetectionWindow]

class GetCarsByRadarIn:
    def __init__(
        self,
        codcet: str = Query(
            ...,
            description="CODCET to get cars by",
            min_length=10,
            max_length=10,
        ),
        start_time: datetime = Query(
            ...,
            description="The start time to get cars by (UTC)",
            example="2021-01-01T00:00:00.000Z",
        ),
        end_time: datetime = Query(
            ...,
            description="The end time to get cars by (UTC)",
            example="2021-01-01T00:00:00.000Z",
        ),
        plate_hint: str = Query(
            None,
            description="The plate hint to get cars by",
            example="ABC1234, A**1234",
            min_length=2, # min plate_hint must be A* (2 characters)
            max_length=7, # max plate_hint must be ABC1D34 (7 characters)
            regex = r"^[a-zA-Z0-9*]{2,7}$" # plate_hint must be alphanumeric and can contain *
        ),
    ):
        self.codcet = codcet
        self.start_time = start_time
        self.end_time = end_time
        self.plate_hint = plate_hint

class GCSUploadIn(BaseModel):
    file_name: str = Field(..., description="The name of the file to upload.")
    content_type: str = Field(..., description="The MIME type of the file.")
    bucket_name: str = Field(..., description="The name of the bucket to upload the file to.")
    file_size: int = Field(..., description="The size of the file in bytes.")
    resumable: bool = Field(False, description="Whether to use resumable upload.")
    file_path: Optional[str] = Field(None, description="The path of the file to upload.")
    crc32c: Optional[str] = Field(None, description="The CRC32C checksum of the file.")
    
    
class GCSUploadOut(BaseModel):
    signed_url: str
    file_exists: bool = Field(..., description="Whether a file with this name already exists in the bucket.")


class GCSFileInfoOut(BaseModel):
    name: str = Field(..., description="The name of the file.")
    size: int = Field(..., description="The size of the file in bytes.")
    content_type: Optional[str] = Field(None, description="The MIME type of the file.")
    time_created: Optional[datetime] = Field(None, description="The time the file was created.")
    updated: Optional[datetime] = Field(None, description="The time the file was last updated.")
    etag: Optional[str] = Field(None, description="The ETag of the file.")


class GCSFileExistsOut(BaseModel):
    exists: bool = Field(..., description="Whether the file exists in the bucket.")
    file_name: str = Field(..., description="The name of the file checked.")
    bucket_name: str = Field(..., description="The name of the bucket.")


class GCSDownloadOut(BaseModel):
    download_url: str = Field(..., description="The signed URL for downloading the file.")
    expires_in_seconds: int = Field(..., description="Number of seconds until the URL expires.")


class GCSDownloadIn(BaseModel):
    file_name: str = Field(..., description="The full path to the file in the bucket (can include folders).")
    bucket_name: str = Field(..., description="The name of the bucket.")
    expiration_minutes: int = Field(15, ge=1, le=10080, description="URL expiration time in minutes (1-10080, max 7 days).")


class GCSFileOrderBy(str, Enum):
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    TIME_CREATED_ASC = "time_created_asc"
    TIME_CREATED_DESC = "time_created_desc"
    SIZE_ASC = "size_asc"
    SIZE_DESC = "size_desc"
    

class ListFilesIn(BaseModel):
    bucket_name: str = Query(..., description="The name of the bucket.")
    order_by: GCSFileOrderBy = Query(
        GCSFileOrderBy.TIME_CREATED_DESC,
        description="Order by field and direction.",
    )
    

class GCSFileExistsIn(BaseModel):
    file_name: str = Field(..., description="The full path to the file in the bucket (can include folders).")
    bucket_name: str = Field(..., description="The name of the bucket.")
    
    
class GCSDeleteFileIn(BaseModel):
    file_name: str = Field(..., description="The full path to the file in the bucket (can include folders).")
    bucket_name: str = Field(..., description="The name of the bucket.")
    
    
MonitoredPlateOut.update_forward_refs()
MonitoredPlateHistory.update_forward_refs()
