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


class Properties(BaseModel):
    index_trip: int
    index_chunk: int
    index: int
    datahora: datetime
    camera_numero: str


class Geometry(BaseModel):
    type: str
    coordinates: List[float]


class Feature(BaseModel):
    type: str
    geometry: Geometry
    properties: Properties


class LocationsGeojson(BaseModel):
    type: str
    features: List[Feature]


class LineStringGeometry(BaseModel):
    type: str
    coordinates: List[List[float]]


class LineStringProperties(BaseModel):
    index_trip: int
    index_chunk: int
    duration: int
    staticDuration: int


class PolylineGeojson(BaseModel):
    type: str
    geometry: LineStringGeometry
    properties: LineStringProperties


class Path(BaseModel):
    locationsChunksGeojson: List[List[LocationsGeojson]]
    polylineChunksGeojson: List[List[PolylineGeojson]]


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
