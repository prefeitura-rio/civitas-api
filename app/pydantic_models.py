from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from enum import Enum

from fastapi import Query
from pydantic import BaseModel, Field, validator

from app.enums import NotificationChannelTypeEnum
from app.models import (
    Demandant,
    MonitoredPlate,
    MonitoredPlateDemandant,
    MonitoredPlateDemandantRadar,
)


class CortexArrendatario(BaseModel):
    enderecoArrendatario: str | None
    id: int | None
    nomeArrendatario: str | None
    numeroDocumentoArrendatario: str | None
    placa: str | None
    tipoDocumentoArrendatario: str | None


class CortexPossuidor(BaseModel):
    enderecoPossuidor: str | None
    id: int | None
    nomePossuidor: str | None
    numeroDocumentoPossuidor: str | None
    placa: str | None
    tipoDocumentoPossuidor: str | None


class CortexProprietario(BaseModel):
    enderecoProprietario: str | None
    id: int | None
    nomeProprietario: str | None
    numeroDocumentoProprietario: str | None
    placa: str | None
    tipoDocumentoProprietario: str | None


class CortexIndiceNacionalVeiculo(BaseModel):
    id: int | None
    metodo: str | None
    qtd: int | None


class CortexRestricao(BaseModel):
    anoBO: str | None
    dataOcorrencia: datetime | None
    dddContato: str | None
    historico: str | None
    id: int | None
    municipioBO: str | None
    naturezaOcorrencia: str | None
    nomeDeclarante: str | None
    numeroBO: str | None
    placa: str | None
    ramalContato: str | None
    sistema: str | None
    telefoneContato: str | None
    ufBO: str | None
    unidadePolicial: str | None


class CortexPlacaOut(BaseModel):
    anoFabricacao: str | None
    anoModelo: str | None
    anoUltimoLicenciamnento: int | None
    arrendatario: CortexArrendatario | None
    capacidadeMaximaCarga: str | None
    capacidadeMaximaTracao: str | None
    carroceria: str | None
    categoria: str | None
    chassi: str | None
    cilindrada: int | None
    codigoCarroceira: int | None
    codigoCategoria: int | None
    codigoCor: int | None
    codigoEspecie: int | None
    codigoMarcaModelo: int | None
    codigoMunicipioEmplacamento: str | None
    codigoOrgaoSRF: str | None
    codigoSegurancaCRV: str | None
    codigoTipoVeiculo: int | None
    combustivel: str | None
    cor: str | None
    dataAtualizacaoAlarme: str | None
    dataAtualizacaoRouboFurto: str | None
    dataAtualizacaoVeiculo: str | None
    dataDeclaracaoImportacao: str | None
    dataEmissaoCRLV: datetime | None
    dataEmissaoUltimoCRV: str | None
    dataEmplacamento: datetime | None
    dataHoraAtualizacaoVeiculo: datetime | None
    dataLimiteRestricaoTributaria: str | None
    dataPreCadastro: str | None
    dataReplicacao: datetime | None
    descricaoOrgaoRegiaoFiscal: str | None
    especie: str | None
    flagAtivo: bool | None
    grupoVeiculo: str | None
    id: int | None
    identificadorUnicoVeiculo: str | None
    indicadorRemarcacaoChassi: bool | None
    indicadorVeiculoLicenciadoCirculacao: str | None
    indicadorVeiculoNacional: bool | None
    indiceNacionalVeiculos: list[CortexIndiceNacionalVeiculo] | None
    lotacao: str | None
    marcaModelo: str | None
    mesAnoValidadeLicenciamento: int | None
    mesFabricacaoVeiculo: str | None
    municipioPlaca: str | None
    nomeArrendatario: str | None
    nomePossuidor: str | None
    nomeProprietario: str | None
    numeroCRV: str | None
    numeroCaixaCambio: str | None
    numeroCarroceria: str | None
    numeroDeclaracaoImportacao: str | None
    numeroEixoAuxiliar: str | None
    numeroEixoTraseiro: str | None
    numeroIdentificacaoFaturado: str | None
    numeroIdentificacaoImportador: str | None
    numeroLicencaUsoConfiguracaoVeiculosMotor: str | None
    numeroMotor: str | None
    numeroProcessoImportacao: str | None
    numeroSequenciaCRV: str | None
    numeroTipoCRLV: str | None
    numeroViaCRLV: int | None
    numeroViaCRV: int | None
    origemPossuidor: str | None
    paisTransferenciaVeiculo: str | None
    pesoBrutoTotal: str | None
    placa: str | None
    placaPreMercosul: str | None
    possuidor: CortexPossuidor | None
    potencia: int | None
    proprietario: CortexProprietario | None
    quantidadeEixo: str | None
    quantidadeRestricoesBaseEmplacamento: str | None
    registroAduaneiro: str | None
    renavam: str | None
    restricao: list[CortexRestricao] | None
    restricaoVeiculo1: str | None
    restricaoVeiculo2: str | None
    restricaoVeiculo3: str | None
    restricaoVeiculo4: str | None
    situacaoVeiculo: str | None
    tipoDocumentoFaturado: str | None
    tipoDocumentoProprietario: str | None
    tipoMontagem: str | None
    tipoVeiculo: str | None
    ufDestinoVeiculoFaturado: str | None
    ufEmplacamento: str | None
    ufFatura: str | None
    ufJurisdicaoVeiculo: str | None
    valorIPVA: int | None
    created_at: datetime | None
    updated_at: datetime | None


class CortexPlacasIn(BaseModel):
    plates: list[str]
    raise_for_errors: bool | None = True


class CortexIndiceNacionalPessoa(BaseModel):
    id: int | None
    metodo: str | None
    qtd: int | None


class CortexPersonOut(BaseModel):
    anoExercicioOcupacao: str | None
    anoObito: str | None
    bairro: str | None
    cep: str | None
    complementoLogradouro: str | None
    dataAtualizacao: datetime | None
    dataNascimento: str | None
    ddd: str | None
    id: int | None
    identificadorResidenteExterior: str | None
    indicadorEstrangeiro: str | None
    indicadorMoradorEstrangeiro: bool | None
    indiceNacionalPessoas: list[CortexIndiceNacionalPessoa] | None
    latitudeAproximadaLocal: float | None
    logradouro: str | None
    longitudeAproximadaLocal: float | None
    municipio: str | None
    municipioNaturalidade: str | None
    naturezaOcupacao: str | None
    nomeCompleto: str | None
    nomeMae: str | None
    nomeSocial: str | None
    numeroCPF: str | None
    numeroLogradouro: str | None
    ocupacaoPrincipal: str | None
    paisNascimento: str | None
    paisResidencia: str | None
    regiaoFiscal: str | None
    sexo: str | None
    situacaoCadastral: str | None
    telefone: str | None
    tipoLogradouro: str | None
    tituloEleitor: str | None
    uf: str | None
    ufNaturalidade: str | None
    created_at: datetime | None
    updated_at: datetime | None


class CortexPeopleIn(BaseModel):
    cpfs: list[str]


class CortexCnpjContador(BaseModel):
    classificacaoCRCContadorPF: str | None
    classificacaoCRCEmpresaContabil: str | None
    cnpjEmpresaContabil: str | None
    crcEmpresaContabil: str | None
    nomeContador: str | None
    numeroCPFContador: str | None
    numeroRegistroContadorPF: str | None
    tipoCRCContadorPF: str | None
    tipoCRCEmpresaContabil: str | None
    ufCRCContador: str | None
    ufCRCEmpresaContabil: str | None


class CortexCnpjSocio(BaseModel):
    cpfRepresentanteLegal: str | None
    dataEntradaSociedade: str | None
    identificadorSocio: str | None
    nomeRepresentanteLegal: str | None
    nomeSocio: str | None
    numeroCPF: str | None
    paisSocioEstrangeiro: str | None
    percentualCapitalSocial: float | None
    qualificacaoRepresentanteLegal: str | None
    qualificacaoSocio: str | None


class CortexSucessao(BaseModel):
    cnpjSucedida: str | None
    cnpjSucessora: str | None
    dataOperacaoSucessora: str | None
    operacaoRealizadaSucessora: str | None
    razaoSocialSucedida: str | None
    razaoSocialSucessora: str | None


class CortexCompanyOut(BaseModel):
    bairro: str | None
    capitalSocialEmpresa: str | None
    cep: str | None
    cnaeFiscal: str | None
    cnaeSecundario: str | None
    cnpj: str | None
    cnpjContador: list[CortexCnpjContador] | None
    cnpjSocio: list[CortexCnpjSocio] | None
    codigoCnaeFiscal: str | None
    codigoCnaeSecundario: str | None
    complementoLogradouro: str | None
    cpfResponsavel: str | None
    dataExclusaoSimples: str | None
    dataInicioAtividade: str | None
    dataOpcaoSimples: str | None
    dataSituacaoCadastral: str | None
    email: str | None
    fax: str | None
    indicadorMatrizFilial: str | None
    logradouro: str | None
    motivoSituacaoCadastral: str | None
    municipio: str | None
    naturezaJuridica: str | None
    nomeCidadeExterior: str | None
    nomeFantasia: str | None
    nomePais: str | None
    nomeResponsavel: str | None
    numeroLogradouro: str | None
    opcaoSimples: str | None
    porteEmpresa: str | None
    qualificacaoPessoaJuridicaResponsavelEmpresa: str | None
    razaoSocial: str | None
    situacaoCadastral: str | None
    sucessao: list[CortexSucessao] | None
    telefone1: str | None
    telefone2: str | None
    tipoLogradouro: str | None
    uf: str | None
    created_at: datetime | None
    updated_at: datetime | None


class CortexCompaniesIn(BaseModel):
    cnpjs: list[str]


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
    email: str | None = None
    email_verified: bool | None
    name: str | None = None
    given_name: str | None = None
    preferred_username: str | None = None
    nickname: str
    groups: list[str]
    matricula: str | None = None
    orgao: str | None = None
    setor: str | None = None
    cpf: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class Location(BaseModel):
    datahora: datetime
    codcet: str
    latitude: float
    longitude: float
    bairro: str | None = None
    sentido: str | None = None
    localidade: str
    velocidade: float
    seconds_to_next_point: float | None = None


class Step(BaseModel):
    distanceMeters: int | None = None
    staticDuration: str
    polyline: dict
    startLocation: dict
    endLocation: dict
    navigationInstruction: dict | None = None
    localizedValues: dict
    travelMode: str


class Leg(BaseModel):
    distanceMeters: int | None = None
    duration: str
    staticDuration: str
    polyline: dict
    startLocation: dict
    endLocation: dict
    steps: list[Step]
    localizedValues: dict


class Route(BaseModel):
    legs: list[Leg]


class Polyline(BaseModel):
    routes: list[Route]


class LocationsItem(BaseModel):
    locations: list[list[Location]]


class PolylineItem(BaseModel):
    polyline: list[Polyline]


class Path(BaseModel):
    locations: list[list[Location]]
    polyline: list[Polyline] | None = None


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


def _normalize_lpr_equipment_ids(v: list | None) -> list[str] | None:
    """Aceita strings (código LPR no BigQuery) ou UUID legado; normaliza e valida tamanho."""
    if v is None:
        return None
    out: list[str] = []
    for x in v:
        s = str(x).strip()
        if not s:
            raise ValueError("lpr_equipment_ids cannot contain empty values")
        if len(s) > 64:
            raise ValueError("each lpr_equipment_id must be at most 64 characters")
        out.append(s)
    return out


class MonitoredPlateDemandantLinkIn(BaseModel):
    demandant_id: UUID
    reference_number: str = Field(..., max_length=50)
    valid_until: datetime | None = None
    notes: str | None = None
    additional_info: dict | None = None
    lpr_equipment_ids: list[str] | None = None

    @validator("lpr_equipment_ids")
    def validate_lpr_equipment_ids(cls, value):
        return _normalize_lpr_equipment_ids(value)


class MonitoredPlateDemandantLinkPatch(BaseModel):
    """Atualização parcial de um vínculo placa–demandante (só campos enviados são aplicados)."""

    reference_number: str | None = Field(default=None, max_length=50)
    valid_until: datetime | None = None
    active: bool | None = None
    notes: str | None = None
    additional_info: dict | None = None
    lpr_equipment_ids: list[str] | None = None

    @validator("lpr_equipment_ids")
    def validate_lpr_equipment_ids_patch(cls, value):
        return _normalize_lpr_equipment_ids(value)


class MonitoredPlateIn(BaseModel):
    plate: str = Field(...)
    notes: str | None = None
    notification_channels: list[UUID] | None = None
    demandant_links: list[MonitoredPlateDemandantLinkIn] | None = None

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


class OrganizationOut(BaseModel):
    id: UUID
    name: str
    organization_type: str
    acronym: str
    jurisdiction_level: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True


class DemandantOut(BaseModel):
    id: UUID
    organization: OrganizationOut
    name: str | None = None
    email: str | None = None
    phone_1: str | None = None
    phone_2: str | None = None
    phone_3: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True

    @classmethod
    async def from_demandant(cls, demandant: Demandant) -> "DemandantOut":
        org = await demandant.organization
        return cls(
            id=demandant.id,
            organization=OrganizationOut.from_orm(org),
            name=demandant.name,
            email=demandant.email,
            phone_1=demandant.phone_1,
            phone_2=demandant.phone_2,
            phone_3=demandant.phone_3,
            created_at=demandant.created_at,
            updated_at=demandant.updated_at,
        )


class MonitoredPlateDemandantRadarOut(BaseModel):
    id: UUID
    lpr_equipment_id: str
    active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True

    @classmethod
    def from_radar_link(
        cls, row: MonitoredPlateDemandantRadar
    ) -> "MonitoredPlateDemandantRadarOut":
        return cls(
            id=row.id,
            lpr_equipment_id=row.lpr_equipment_id,
            active=row.active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class MonitoredPlateDemandantLinkOut(BaseModel):
    id: UUID
    reference_number: str
    valid_until: datetime | None = None
    active: bool
    validity_warning_sent_at: datetime | None = None
    notes: str | None = None
    additional_info: dict | None = None
    demandant: DemandantOut
    radars: list[MonitoredPlateDemandantRadarOut] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True


class MonitoredPlateOut(BaseModel):
    id: UUID
    plate: str
    notes: str | None = None
    notification_channels: list["NotificationChannelOut"] | None = []
    demandant_links: list[MonitoredPlateDemandantLinkOut] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True

    @classmethod
    async def from_monitored_plate(cls, monitored_plate: MonitoredPlate):
        channels = await monitored_plate.notification_channels.all()
        links_qs = MonitoredPlateDemandant.filter(
            monitored_plate_id=monitored_plate.id
        ).prefetch_related("demandant__organization", "radar_links")
        links = await links_qs
        demandant_links_out: list[MonitoredPlateDemandantLinkOut] = []
        for link in links:
            demandant_obj = await link.demandant
            radars = await link.radar_links.all()
            demandant_links_out.append(
                MonitoredPlateDemandantLinkOut(
                    id=link.id,
                    reference_number=link.reference_number,
                    valid_until=link.valid_until,
                    active=link.active,
                    validity_warning_sent_at=link.validity_warning_sent_at,
                    notes=link.notes,
                    additional_info=link.additional_info,
                    demandant=await DemandantOut.from_demandant(demandant_obj),
                    radars=[
                        MonitoredPlateDemandantRadarOut.from_radar_link(r)
                        for r in radars
                    ],
                    created_at=link.created_at,
                    updated_at=link.updated_at,
                )
            )
        return MonitoredPlateOut(
            id=monitored_plate.id,
            plate=monitored_plate.plate,
            notes=monitored_plate.notes,
            notification_channels=[
                NotificationChannelOut.from_orm(ch) for ch in channels
            ],
            demandant_links=demandant_links_out,
            created_at=monitored_plate.created_at,
            updated_at=monitored_plate.updated_at,
        )


class MonitoredPlateHistory(BaseModel):
    plate: str
    notes: str | None = None
    created_timestamp: datetime | None = None
    created_by: Optional["UserOut"] = None
    deleted_timestamp: datetime | None = None
    deleted_by: Optional["UserOut"] = None


class MonitoredPlateUpdate(BaseModel):
    plate: str | None = Field(default=None)
    notes: str | None = None
    notification_channels: list[UUID] | None = None

    @validator("plate")
    def validate_plate(cls, value: str):
        from app.utils import validate_plate as validate_plate_util

        if value is not None:
            value = value.upper()

        if value is not None and not validate_plate_util(value):
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
    title: str | None = None
    channel_type: NotificationChannelTypeEnum
    parameters: dict
    active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True


class NotificationChannelUpdate(BaseModel):
    title: str | None = None
    active: bool | None = None


class NPlatesBeforeAfterDetection(BaseModel):
    timestamp: datetime | None = None
    plate: str
    codcet: str
    lane: str
    speed: float | None = None
    count: int | None = None


class NPlatesBeforeAfterOut(BaseModel):
    radars: list[str] = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    detection_time: datetime | None = None
    total_detections: int | None = None
    detections: list[NPlatesBeforeAfterDetection] = None


class OrganizationIn(BaseModel):
    name: str
    organization_type: str
    acronym: str
    jurisdiction_level: str


class OrganizationUpdate(BaseModel):
    name: str | None = None
    organization_type: str | None = None
    acronym: str | None = None
    jurisdiction_level: str | None = None


class DemandantIn(BaseModel):
    organization_id: UUID
    name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone_1: str | None = Field(default=None, max_length=20)
    phone_2: str | None = Field(default=None, max_length=20)
    phone_3: str | None = Field(default=None, max_length=20)


class DemandantUpdate(BaseModel):
    organization_id: UUID | None = None
    name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone_1: str | None = Field(default=None, max_length=20)
    phone_2: str | None = Field(default=None, max_length=20)
    phone_3: str | None = Field(default=None, max_length=20)


class RadarOut(BaseModel):
    codcet: str
    latitude: float
    longitude: float
    locequip: str | None = None
    bairro: str | None = None
    logradouro: str | None = None
    has_data: str
    empresa: str | None = None
    active_in_last_24_hours: str | None = None
    last_detection_time: datetime | None = None
    sentido: str | None = None


class ReportFilters(BaseModel):
    limit: int
    offset: int
    semantically_similar: str | None = None
    id_report: str | None = None
    id_report_original: str | None = None
    id_source_contains: list[str] | None = None
    data_report_min: datetime | None = None
    data_report_max: datetime | None = None
    categoria_contains: list[str] | None = None
    descricao_contains: list[str] | None = None
    keywords: list[str] | None = None
    latitude_min: float | None = None
    latitude_max: float | None = None
    longitude_min: float | None = None
    longitude_max: float | None = None


class ReportTipoSubtipo(BaseModel):
    tipo: str
    subtipo: list[str]


class ReportAdditionalInfo(BaseModel):
    certainty: float


class ReportOut(BaseModel):
    id_report: str
    id_source: str
    id_report_original: str
    data_report: datetime
    orgaos: list[str]
    categoria: str
    tipo_subtipo: list[ReportTipoSubtipo]
    descricao: str | None = None
    logradouro: str | None = None
    numero_logradouro: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    updated_at: datetime
    additional_info: ReportAdditionalInfo | None = None


class ReportLatLongOut(BaseModel):
    id_report: str
    latitude: float | None = None
    longitude: float | None = None


class ReportTimelineOut(BaseModel):
    data_report: datetime
    id_source: str
    count: int


class ReportTopSubtypesOut(BaseModel):
    tipo: str
    subtipo: str | None = None
    count: int


class ReportsMetadata(BaseModel):
    distinct_sources: list[str]
    distinct_categories: list[str]
    distinct_types: list[str]
    type_subtypes: dict[str, list[str]]


class UserCortexRemainingCreditOut(BaseModel):
    remaining_credit: int
    time_until_reset: int


class UserHistoryOut(BaseModel):
    id: UUID
    method: str
    path: str
    query_params: dict | None = None
    body: dict | None = None
    status_code: int
    timestamp: datetime


class UserOut(BaseModel):
    id: UUID
    username: str
    full_name: str | None = None
    cpf: str | None = None
    registration: str | None = None
    agency: str | None = None
    sector: str | None = None
    email: str | None = None
    is_admin: bool

    class Config:
        orm_mode = True


class WazeAlertOut(BaseModel):
    timestamp: datetime
    street: str | None = None
    type: str
    subtype: str
    reliability: float
    confidence: float
    number_thumbs_up: int | None = None
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
    radars: list[str]
    start_time: datetime
    end_time: datetime
    location: str
    latitude: float
    longitude: float
    detection_time: datetime
    total_detections: int
    detections: list[PdfReportCorrelatedPlatesDataDetection]


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
    report_data: list[PdfReportCorrelatedPlatesData] = []
    params: PdfReportCorrelatedPlatesParams
    ranking: list[PdfReportCorrelatedPlatesRanking] = []


class RequestedPlateData(BaseModel):
    plate: str
    start: datetime
    end: datetime
    n_minutes: int | None = None
    n_plates: int | None = None
    target_id: int | None = None


class VehicleType(str, Enum):
    AUTOMOVEL = "automovel"
    CAMINHAO = "caminhao"
    CAMINHAO_ONIBUS = "caminhao_onibus"
    CICLOMOTOR = "ciclomotor"
    INDEFINIDO = "indefinido"
    MOTO = "moto"
    ONIBUS = "onibus"


class PdfReportMultipleCorrelatedPlatesIn(BaseModel):
    requested_plates_data: list[RequestedPlateData]
    n_minutes: int = Field(gt=0, le=20, description="Must be between 1 and 20")
    n_plates: int | None = Field(gt=0, description="Must be greater than 0")
    min_different_targets: int = Field(gt=0, description="Must be greater than 0")
    # vehicle_types: List[VehicleType] = Field(
    #     default=[VehicleType.AUTOMOVEL, VehicleType.INDEFINIDO],
    #     description="Must be a list of vehicle types."
    # )
    keep_buses: bool = Field(default=False, description="Must be a boolean")
    before_after: Literal["before", "after"] | None
    report_title: str = "Relatório de Identificação de Veículos"


class DetectionWindow(BaseModel):
    plate: str
    codcet: str
    detection_index: int
    target_id: int
    n_minutes: int
    n_plates: int | None = None
    start_time: datetime
    end_time: datetime
    local_detection_datetime: datetime
    start_window: datetime
    end_window: datetime


class DetectionWindowList(BaseModel):
    detection_window_list: list[DetectionWindow]


class GetCarsByRadarIn:
    def __init__(
        self,
        codcet: str = Query(
            ...,
            description="CODCET to get cars by",
            # min_length=10,
            # max_length=10,
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
            min_length=2,  # min plate_hint must be A* (2 characters)
            max_length=7,  # max plate_hint must be ABC1D34 (7 characters)
            regex=r"^[a-zA-Z0-9*]{2,7}$",  # plate_hint must be alphanumeric and can contain *
        ),
    ):
        self.codcet = codcet
        self.start_time = start_time
        self.end_time = end_time
        self.plate_hint = plate_hint


class GCSUploadIn(BaseModel):
    file_name: str = Field(..., description="The name of the file to upload.")
    content_type: str = Field(..., description="The MIME type of the file.")
    bucket_name: str = Field(
        ..., description="The name of the bucket to upload the file to."
    )
    file_size: int = Field(..., description="The size of the file in bytes.")
    resumable: bool = Field(False, description="Whether to use resumable upload.")
    file_path: str | None = Field(None, description="The path of the file to upload.")
    crc32c: str | None = Field(None, description="The CRC32C checksum of the file.")


class GCSUploadOut(BaseModel):
    signed_url: str
    file_exists: bool = Field(
        ..., description="Whether a file with this name already exists in the bucket."
    )


class GCSFileInfoOut(BaseModel):
    name: str = Field(..., description="The name of the file.")
    size: int = Field(..., description="The size of the file in bytes.")
    content_type: str | None = Field(None, description="The MIME type of the file.")
    time_created: datetime | None = Field(
        None, description="The time the file was created."
    )
    updated: datetime | None = Field(
        None, description="The time the file was last updated."
    )
    etag: str | None = Field(None, description="The ETag of the file.")


class GCSFileExistsOut(BaseModel):
    exists: bool = Field(..., description="Whether the file exists in the bucket.")
    file_name: str = Field(..., description="The name of the file checked.")
    bucket_name: str = Field(..., description="The name of the bucket.")


class GCSDownloadOut(BaseModel):
    download_url: str = Field(
        ..., description="The signed URL for downloading the file."
    )
    expires_in_seconds: int = Field(
        ..., description="Number of seconds until the URL expires."
    )


class GCSDownloadIn(BaseModel):
    file_name: str = Field(
        ...,
        description="The full path to the file in the bucket (can include folders).",
    )
    bucket_name: str = Field(..., description="The name of the bucket.")
    expiration_minutes: int = Field(
        15,
        ge=1,
        le=10080,
        description="URL expiration time in minutes (1-10080, max 7 days).",
    )


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
    file_name: str = Field(
        ...,
        description="The full path to the file in the bucket (can include folders).",
    )
    bucket_name: str = Field(..., description="The name of the bucket.")


class GCSDeleteFileIn(BaseModel):
    file_name: str = Field(
        ...,
        description="The full path to the file in the bucket (can include folders).",
    )
    bucket_name: str = Field(..., description="The name of the bucket.")


MonitoredPlateOut.update_forward_refs()
MonitoredPlateHistory.update_forward_refs()



class OperationTitleSearchOut(BaseModel):
    id: str
    title: str