# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query, Request
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page

from app.decorators import router_request
from app.dependencies import get_user
from app.models import User
from app.pydantic_models import ReportFilters, ReportOut, ReportsMetadata
from app.utils import get_reports_metadata, search_weaviate

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(
    method="GET",
    router=router,
    path="",
    response_model=Page[ReportOut],
)
async def get_reports(
    user: Annotated[User, Depends(get_user)],
    request: Request,
    semantically_similar: str = None,
    id_report: str = None,
    id_report_original: str = None,
    id_source_contains: List[str] = Query(None),
    data_report_min: datetime = None,
    data_report_max: datetime = None,
    categoria_contains: List[str] = Query(None),
    descricao_contains: List[str] = Query(None),
    latitude_min: float = None,
    latitude_max: float = None,
    longitude_min: float = None,
    longitude_max: float = None,
    params: Params = Depends(),
):
    offset = params.size * (params.page - 1)
    filters = ReportFilters(
        limit=params.size,
        offset=offset,
        semantically_similar=semantically_similar,
        id_report=id_report,
        id_report_original=id_report_original,
        id_source_contains=id_source_contains,
        data_report_min=data_report_min,
        data_report_max=data_report_max,
        categoria_contains=categoria_contains,
        descricao_contains=descricao_contains,
        latitude_min=latitude_min,
        latitude_max=latitude_max,
        longitude_min=longitude_min,
        longitude_max=longitude_max,
    )

    reports = await search_weaviate(filters)
    return create_page(reports, params=params, total=len(reports))


@router_request(
    method="GET",
    router=router,
    path="/categories",
    response_model=List[str],
)
async def get_report_categories(
    user: Annotated[User, Depends(get_user)],
    request: Request,
):
    metadata: ReportsMetadata | dict = await get_reports_metadata()
    if isinstance(metadata, dict):
        metadata = ReportsMetadata(**metadata)
    return metadata.distinct_categories


@router_request(
    method="GET",
    router=router,
    path="/sources",
    response_model=List[str],
)
async def get_report_sources(
    user: Annotated[User, Depends(get_user)],
    request: Request,
):
    metadata: ReportsMetadata | dict = await get_reports_metadata()
    if isinstance(metadata, dict):
        metadata = ReportsMetadata(**metadata)
    return metadata.distinct_sources


@router_request(
    method="GET",
    router=router,
    path="/subtypes",
    response_model=List[str],
)
async def get_report_subtypes(
    user: Annotated[User, Depends(get_user)],
    request: Request,
    type: List[str] = Query(None),
):
    metadata: ReportsMetadata | dict = await get_reports_metadata()
    if isinstance(metadata, dict):
        metadata = ReportsMetadata(**metadata)
    if not type:
        distinct_subtypes = []
        for k, v in metadata.type_subtypes.items():
            distinct_subtypes.extend(v)
        return list(set(distinct_subtypes))
    else:
        distinct_subtypes = []
        for t in type:
            distinct_subtypes.extend(metadata.type_subtypes.get(t, []))
        return list(set(distinct_subtypes))


@router_request(
    method="GET",
    router=router,
    path="/types",
    response_model=List[str],
)
async def get_report_types(
    user: Annotated[User, Depends(get_user)],
    request: Request,
):
    metadata: ReportsMetadata | dict = await get_reports_metadata()
    if isinstance(metadata, dict):
        metadata = ReportsMetadata(**metadata)
    return metadata.distinct_types
