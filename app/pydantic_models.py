# -*- coding: utf-8 -*-
import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.enums import ActionTypeEnum, NotificationChannelTypeEnum
from app.models import Group, GroupUser


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
    additional_info: Optional[dict] = None
    notification_channels: Optional[List[UUID]] = []

    class Config:
        orm_mode = True


class MonitoredPlateUpdate(BaseModel):
    additional_info: Optional[dict] = None
    notification_channels: Optional[List[UUID]] = None


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


class PermissionIn(BaseModel):
    action: ActionTypeEnum
    resource: UUID


class PermissionOut(BaseModel):
    id: UUID
    action: ActionTypeEnum
    resource: UUID

    class Config:
        orm_mode = True


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


GroupOut.update_forward_refs()
GroupUserOut.update_forward_refs()
