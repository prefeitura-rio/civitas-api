# -*- coding: utf-8 -*-
import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.enums import ActionTypeEnum, NotificationChannelTypeEnum
from app.models import Group, GroupUser, MonitoredPlate


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
    camera_numero: str
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


class GroupIn(BaseModel):
    name: str
    description: Optional[str] = None
    users: Optional[List[UUID]] = None


class GroupOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    users: List["GroupUserOut"] = []

    @classmethod
    async def from_group(cls, group: Group):
        group_users = await GroupUser.filter(group=group).prefetch_related("user").all()
        users = []
        for group_user in group_users:
            users.append(
                GroupUserOut(
                    user=UserOut.from_orm(group_user.user),
                    is_group_admin=group_user.is_group_admin,
                )
            )
        return GroupOut(id=group.id, name=group.name, description=group.description, users=users)


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class GroupUserIn(BaseModel):
    user: UUID
    is_group_admin: bool


class GroupUserOut(BaseModel):
    user: "UserOut"
    is_group_admin: bool


class GroupUserUpdate(BaseModel):
    is_group_admin: Optional[bool] = None


class MonitoredPlateIn(BaseModel):
    plate: str = Field(...)
    operation_id: UUID
    active: Optional[bool] = True
    notes: Optional[str] = None
    additional_info: Optional[dict] = None
    notification_channels: Optional[List[UUID]] = None

    @validator("plate")
    def validate_plate(cls, value: str):
        # Ensure the plate is upper case
        value = value.upper()

        # Ensure the plate has the correct format
        pattern = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")
        if not pattern.match(value):
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
    notes: Optional[str] = None
    additional_info: Optional[dict] = None
    notification_channels: Optional[List["NotificationChannelOut"]] = []

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
            notes=monitored_plate.notes,
            additional_info=monitored_plate.additional_info,
            notification_channels=[
                NotificationChannelOut.from_orm(channel)
                for channel in await monitored_plate.notification_channels.all()
            ],
        )


class MonitoredPlateUpdate(BaseModel):
    plate: Optional[str] = Field(default=None)
    operation_id: Optional[UUID] = None
    active: Optional[bool] = None
    notes: Optional[str] = None
    additional_info: Optional[dict] = None
    notification_channels: Optional[List[UUID]] = None

    @validator("plate")
    def validate_plate(cls, value: str):
        if value is not None:
            # Ensure the plate is upper case
            value = value.upper()

            # Ensure the plate has the correct format
            pattern = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")
            if not pattern.match(value):
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

    class Config:
        orm_mode = True


class NotificationChannelUpdate(BaseModel):
    title: Optional[str] = None
    active: Optional[bool] = None


class OperationIn(BaseModel):
    title: str
    description: Optional[str] = None


class OperationOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None

    class Config:
        orm_mode = True


class OperationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class PermissionIn(BaseModel):
    action: ActionTypeEnum
    resource: UUID


class PermissionOut(BaseModel):
    id: UUID
    action: ActionTypeEnum
    resource: UUID

    class Config:
        orm_mode = True


class RadarOut(BaseModel):
    codcet: str
    camera_numero: str
    latitude: float
    longitude: float
    locequip: str
    bairro: str
    logradouro: str
    has_data: str
    empresa: Optional[str] = None
    active_in_last_24_hours: Optional[str] = None
    last_detection_time: Optional[datetime] = None
    sentido: Optional[str] = None


class ResourceOut(BaseModel):
    id: UUID
    name: str

    class Config:
        orm_mode = True


class RoleIn(BaseModel):
    name: str
    description: Optional[str] = None
    users: Optional[List[UUID]] = None
    permissions: Optional[List[UUID]] = None


class RoleOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    users: List[UUID] = []
    permissions: List[UUID] = []

    class Config:
        orm_mode = True


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleUserIn(BaseModel):
    user: UUID


class RolePermissionIn(BaseModel):
    permission: UUID


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
    latitude_min: Optional[float] = None
    latitude_max: Optional[float] = None
    longitude_min: Optional[float] = None
    longitude_max: Optional[float] = None


class ReportOrgao(BaseModel):
    nome: str


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
    orgaos: List[ReportOrgao]
    categoria: str
    tipo_subtipo: List[ReportTipoSubtipo]
    descricao: str
    logradouro: str
    numero_logradouro: str
    latitude: float
    longitude: float
    additional_info: Optional[ReportAdditionalInfo] = None


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


GroupOut.update_forward_refs()
GroupUserOut.update_forward_refs()
MonitoredPlateOut.update_forward_refs()
