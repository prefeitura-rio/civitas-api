# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


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
    email: str | None
    email_verified: bool | None
    name: str | None
    given_name: str | None
    preferred_username: str | None
    nickname: str
    groups: list[str]


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
    is_admin: bool

    class Config:
        orm_mode = True
