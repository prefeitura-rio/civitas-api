# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from app.modules.tickets.domain.enum import TicketPriority, TicketStatus
from pydantic import BaseModel, EmailStr, Field, HttpUrl

class TicketCatalogCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=50_000)
    is_active: bool = True


class TicketCatalogUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=50_000)
    is_active: Optional[bool] = None


class TicketNatureOut(BaseModel):
    id: str
    created_at: datetime
    name: str
    description: Optional[str] = None
    is_active: bool


class TicketTypeOut(BaseModel):
    id: str
    created_at: datetime
    name: str
    description: Optional[str] = None
    is_active: bool


class TicketNatureListItemOut(BaseModel):
    id: str
    created_at: datetime
    name: str
    is_active: bool


class TicketTypeListItemOut(BaseModel):
    id: str
    created_at: datetime
    name: str
    is_active: bool


class TicketNaturePageOut(BaseModel):
    items: List[TicketNatureListItemOut]
    total: int


class TicketTypePageOut(BaseModel):
    items: List[TicketTypeListItemOut]
    total: int



class TicketDetection(str, Enum):
    antes = "ANTES"
    depois = "DEPOIS"
    ambos = "AMBOS"


class ServiceBuscaPorPlacaIn(BaseModel):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    plate: str = Field(min_length=1, max_length=20)


class ServiceBuscaPorRadarIn(BaseModel):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    plate: str = Field(min_length=1, max_length=20)
    radar_address: Optional[str] = Field(default=None, max_length=50_000)


class ServiceCercoEletronicoIn(BaseModel):
    plate: str = Field(min_length=1, max_length=20)
    vehicle_observations: Optional[str] = Field(default=None, max_length=50_000)


class ServiceBuscaPorImagemIn(BaseModel):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    plate: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=50_000)
    description: Optional[str] = Field(default=None, max_length=50_000)


class ServicePlacasCorrelatasItemIn(BaseModel):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    plate: str = Field(min_length=1, max_length=20)


class ServicePlacasCorrelatasIn(BaseModel):
    interest_interval_minutes: Optional[int] = Field(default=None, ge=0)
    detection_count: Optional[int] = Field(default=None, ge=0)
    detection: Optional[TicketDetection] = None
    items: List[ServicePlacasCorrelatasItemIn] = Field(default_factory=list)


class ServicePlacasConjuntasItemIn(BaseModel):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    plate: str = Field(min_length=1, max_length=20)


class ServicePlacasConjuntasIn(BaseModel):
    interest_interval_minutes: Optional[int] = Field(default=None, ge=0)
    detection_count: Optional[int] = Field(default=None, ge=0)
    detection: Optional[TicketDetection] = None
    items: List[ServicePlacasConjuntasItemIn] = Field(default_factory=list)


class ServiceReservaDeImagemIn(BaseModel):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    orientation: Optional[str] = Field(default=None, max_length=50_000)


class ServiceAnaliseDeImagemIn(BaseModel):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    orientation: Optional[str] = Field(default=None, max_length=50_000)


class ServiceOutrosIn(BaseModel):
    orientation: Optional[str] = Field(default=None, max_length=50_000)


class ServiceBuscaPorPlacaOut(ServiceBuscaPorPlacaIn):
    id: str
    created_at: datetime


class ServiceBuscaPorRadarOut(ServiceBuscaPorRadarIn):
    id: str
    created_at: datetime


class ServiceCercoEletronicoOut(ServiceCercoEletronicoIn):
    id: str
    created_at: datetime


class ServiceBuscaPorImagemOut(ServiceBuscaPorImagemIn):
    id: str
    created_at: datetime


class ServicePlacasCorrelatasItemOut(ServicePlacasCorrelatasItemIn):
    id: str
    created_at: datetime


class ServicePlacasCorrelatasOut(BaseModel):
    id: str
    created_at: datetime
    interest_interval_minutes: Optional[int] = None
    detection_count: Optional[int] = None
    detection: Optional[TicketDetection] = None
    items: List[ServicePlacasCorrelatasItemOut] = Field(default_factory=list)


class ServicePlacasConjuntasItemOut(ServicePlacasConjuntasItemIn):
    id: str
    created_at: datetime


class ServicePlacasConjuntasOut(BaseModel):
    id: str
    created_at: datetime
    interest_interval_minutes: Optional[int] = None
    detection_count: Optional[int] = None
    detection: Optional[TicketDetection] = None
    items: List[ServicePlacasConjuntasItemOut] = Field(default_factory=list)


class ServiceReservaDeImagemOut(ServiceReservaDeImagemIn):
    id: str
    created_at: datetime


class ServiceAnaliseDeImagemOut(ServiceAnaliseDeImagemIn):
    id: str
    created_at: datetime


class ServiceOutrosOut(ServiceOutrosIn):
    id: str
    created_at: datetime


class TicketCreateRequester(BaseModel):
    requisitante_nome: str = Field(min_length=2, max_length=120)
    requisitante_telefone: Optional[str] = Field(default=None, max_length=30)
    requisitante_email: EmailStr


class TicketCreateFocalPoint(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    telefone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[EmailStr] = None


class TicketCreateIn(BaseModel):
    associar_chamado_id: Optional[str] = None
    tipo_chamado_id: str

    operation_id: str = Field(description="Demandante (FK para Operation)")

    numero_procedimento: Optional[str] = Field(default=None, max_length=60)
    numero_oficio: Optional[str] = Field(default=None, max_length=60)
    data_base: Optional[date] = None
    natureza_id: Optional[str] = None

    possui_apelido_imprensa: bool = False
    apelido_imprensa: Optional[str] = Field(default=None, max_length=120)
    link_materia: Optional[HttpUrl] = None

    requisitante: TicketCreateRequester
    pontos_focais: List[TicketCreateFocalPoint] = Field(default_factory=list)

    equipe_id: str
    prioridade: TicketPriority

    comentario_inicial: Optional[str] = Field(default=None, max_length=50_000)

    busca_por_placa: List[ServiceBuscaPorPlacaIn] = Field(default_factory=list)
    busca_por_radar: List[ServiceBuscaPorRadarIn] = Field(default_factory=list)
    cerco_eletronico: List[ServiceCercoEletronicoIn] = Field(default_factory=list)
    busca_por_imagem: List[ServiceBuscaPorImagemIn] = Field(default_factory=list)
    placas_correlatas: List[ServicePlacasCorrelatasIn] = Field(default_factory=list)
    placas_conjuntas: List[ServicePlacasConjuntasIn] = Field(default_factory=list)
    reserva_de_imagem: List[ServiceReservaDeImagemIn] = Field(default_factory=list)
    analise_de_imagem: List[ServiceAnaliseDeImagemIn] = Field(default_factory=list)
    outros: List[ServiceOutrosIn] = Field(default_factory=list)


class TicketCommentOut(BaseModel):
    id: str
    created_at: datetime
    author_id: Optional[str] = None
    body: str


class TicketAttachmentOut(BaseModel):
    id: str
    filename: str
    content_type: Optional[str] = None
    size_bytes: int
    created_at: datetime


class TicketOut(BaseModel):
    id: str
    criado_em: datetime

    associar_chamado_id: Optional[str]
    tipo_chamado_id: str

    operation_id: Optional[str]

    numero_procedimento: Optional[str]
    numero_oficio: Optional[str]
    data_base: Optional[date]
    natureza_id: Optional[str]

    possui_apelido_imprensa: bool
    apelido_imprensa: Optional[str]
    link_materia: Optional[str]

    requisitante: TicketCreateRequester
    pontos_focais: List[TicketCreateFocalPoint]

    equipe_id: Optional[str]
    prioridade: TicketPriority

    comentarios: List[TicketCommentOut] = Field(default_factory=list)
    anexos: List[TicketAttachmentOut] = Field(default_factory=list)

    busca_por_placa: List[ServiceBuscaPorPlacaOut] = Field(default_factory=list)
    busca_por_radar: List[ServiceBuscaPorRadarOut] = Field(default_factory=list)
    cerco_eletronico: List[ServiceCercoEletronicoOut] = Field(default_factory=list)
    busca_por_imagem: List[ServiceBuscaPorImagemOut] = Field(default_factory=list)
    placas_correlatas: List[ServicePlacasCorrelatasOut] = Field(default_factory=list)
    placas_conjuntas: List[ServicePlacasConjuntasOut] = Field(default_factory=list)
    reserva_de_imagem: List[ServiceReservaDeImagemOut] = Field(default_factory=list)
    analise_de_imagem: List[ServiceAnaliseDeImagemOut] = Field(default_factory=list)
    outros: List[ServiceOutrosOut] = Field(default_factory=list)


class TicketListItemOut(BaseModel):
    id: str
    criado_em: datetime
    tipo_chamado_id: str
    operation_id: Optional[str]
    prioridade: TicketPriority
    natureza_id: Optional[str]
    numero_procedimento: Optional[str]
    numero_oficio: Optional[str]


class PageOut(BaseModel):
    items: List[TicketListItemOut]
    page: int
    page_size: int
    total: int


class TicketSearchOut(BaseModel):
    id: str
    criado_em: datetime
    titulo: str

class TicketCreateResultOut(BaseModel):
    id: str


class TicketDashboardServiceTagOut(BaseModel):
    label: str

class TicketDashboardItemOut(BaseModel):
    id: str
    numero_interno: int
    chamado: str
    status: str
    demandante: str
    equipe: Optional[str] = None
    responsavel: str
    prioridade: str
    dias_atraso: int
    servicos: List[TicketDashboardServiceTagOut]

class TicketDashboardSectionOut(BaseModel):
    total: int
    items: List[TicketDashboardItemOut] = []

class TicketDashboardOut(BaseModel):
    pendentes: TicketDashboardSectionOut
    restritos: TicketDashboardSectionOut
    aguardando_revisao: TicketDashboardSectionOut
    bloqueados: TicketDashboardSectionOut
    concluidos_total: int
    urgentes: TicketDashboardSectionOut
    em_atraso: TicketDashboardSectionOut
    total: int
    period_days: int
    overdue_after_days: int


class TicketOfficialLetterSearchOut(BaseModel):
    numero_oficio: str

class TicketInternalNumberSearchOut(BaseModel):
    numero_interno: int

class TicketProcedureNumberSearchOut(BaseModel):
    numero_procedimento: str

class TicketRequesterSearchOut(BaseModel):
    requisitante: str

class TicketFocalPointSearchOut(BaseModel):
    ponto_focal: str

class TicketDashboardFilterIn(BaseModel):
    period_days: int = Field(default=30, ge=1, le=365)
    overdue_after_days: int = Field(default=7, ge=1, le=365)
    search: Optional[str] = None

    tipo_chamado_id: Optional[List[str]] = None
    numero_interno: Optional[List[int]] = None
    numero_procedimento: Optional[List[str]] = None
    numero_oficio: Optional[List[str]] = None
    natureza_id: Optional[List[str]] = None
    demandante_id: Optional[List[str]] = None
    requisitante: Optional[List[str]] = None
    ponto_focal: Optional[List[str]] = None

    data_base_inicio: Optional[date] = None
    data_base_fim: Optional[date] = None

    data_entrada_inicio: Optional[date] = None
    data_entrada_fim: Optional[date] = None

    status: Optional[List[str]] = None
    prioridade: Optional[List[str]] = None
    equipe: Optional[List[str]] = None
    servicos_realizados: Optional[List[str]] = None