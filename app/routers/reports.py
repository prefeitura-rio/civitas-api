# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from loguru import logger
from pendulum import Date, DateTime

from app.decorators import router_request
from app.dependencies import get_user
from app.models import User
from app.pydantic_models import (
    ReportFilters,
    ReportLatLongOut,
    ReportOut,
    ReportsMetadata,
    ReportTimelineOut,
    ReportTopSubtypesOut,
)
from app.utils import (
    ReportsOrderBy,
    ReportsSearchMode,
    get_reports_metadata,
    search_weaviate,
)

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
    keywords: List[str] = Query(None),
    latitude_min: float = None,
    latitude_max: float = None,
    longitude_min: float = None,
    longitude_max: float = None,
    order_by: ReportsOrderBy = ReportsOrderBy.TIMESTAMP_DESC,
    params: Params = Depends(),
):
    # TODO: re-enable semantically similar search someday
    if semantically_similar:
        raise HTTPException(
            status_code=400,
            detail="Semantically similar search is disabled for now.",
        )
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
        keywords=keywords,
        latitude_min=latitude_min if latitude_min else -90,
        latitude_max=latitude_max if latitude_max else 90,
        longitude_min=longitude_min if longitude_min else -180,
        longitude_max=longitude_max if longitude_max else 180,
    )

    reports, total = await search_weaviate(
        filters=filters, order_by=order_by, search_mode=ReportsSearchMode.FULL
    )
    reports = [ReportOut(**r) for r in reports]
    return create_page(reports, params=params, total=total)


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
    path="/dashboard/map",
    response_model=List[ReportLatLongOut],
)
async def get_reports_dashboard_map(
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
    keywords: List[str] = Query(None),
    latitude_min: float = None,
    latitude_max: float = None,
    longitude_min: float = None,
    longitude_max: float = None,
    order_by: ReportsOrderBy = ReportsOrderBy.TIMESTAMP_DESC,
):
    def get_filters(offset: int, size: int) -> ReportFilters:
        return ReportFilters(
            limit=size,
            offset=offset,
            semantically_similar=semantically_similar,
            id_report=id_report,
            id_report_original=id_report_original,
            id_source_contains=id_source_contains,
            data_report_min=data_report_min,
            data_report_max=data_report_max,
            categoria_contains=categoria_contains,
            descricao_contains=descricao_contains,
            keywords=keywords,
            latitude_min=latitude_min if latitude_min else -90,
            latitude_max=latitude_max if latitude_max else 90,
            longitude_min=longitude_min if longitude_min else -180,
            longitude_max=longitude_max if longitude_max else 180,
        )

    # TODO: re-enable semantically similar search someday
    if semantically_similar:
        raise HTTPException(
            status_code=400,
            detail="Semantically similar search is disabled for now.",
        )
    page_size = 10000
    tasks_batch_size = 5
    initial_filters = get_filters(offset=0, size=page_size)
    reports, total = await search_weaviate(
        filters=initial_filters,
        order_by=order_by,
        search_mode=ReportsSearchMode.LATLONG_ONLY,
    )
    if total > page_size:
        tasks = []
        for offset in range(page_size, total, page_size):
            filters = get_filters(offset=offset, size=page_size)
            tasks.append(
                search_weaviate(
                    filters=filters,
                    order_by=order_by,
                    search_mode=ReportsSearchMode.LATLONG_ONLY,
                )
            )
        # Submit tasks in batches
        for i in range(0, len(tasks), tasks_batch_size):
            logger.debug(
                f"Submitting tasks {i} to {i+tasks_batch_size} of {len(tasks)}"
            )
            results = await asyncio.gather(*tasks[i : i + tasks_batch_size])
            for reports_batch, _ in results:
                reports.extend(reports_batch)

    reports = [ReportLatLongOut(**r) for r in reports]

    return reports


@router_request(
    method="GET",
    router=router,
    path="/dashboard/timeline",
    response_model=List[ReportTimelineOut],
)
async def get_reports_dashboard_timeline(
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
    keywords: List[str] = Query(None),
    latitude_min: float = None,
    latitude_max: float = None,
    longitude_min: float = None,
    longitude_max: float = None,
    order_by: ReportsOrderBy = ReportsOrderBy.TIMESTAMP_DESC,
):
    def get_filters(offset: int, size: int) -> ReportFilters:
        return ReportFilters(
            limit=size,
            offset=offset,
            semantically_similar=semantically_similar,
            id_report=id_report,
            id_report_original=id_report_original,
            id_source_contains=id_source_contains,
            data_report_min=data_report_min,
            data_report_max=data_report_max,
            categoria_contains=categoria_contains,
            descricao_contains=descricao_contains,
            keywords=keywords,
            latitude_min=latitude_min if latitude_min else -90,
            latitude_max=latitude_max if latitude_max else 90,
            longitude_min=longitude_min if longitude_min else -180,
            longitude_max=longitude_max if longitude_max else 180,
        )

    # TODO: re-enable semantically similar search someday
    if semantically_similar:
        raise HTTPException(
            status_code=400,
            detail="Semantically similar search is disabled for now.",
        )
    page_size = 10000
    tasks_batch_size = 5
    initial_filters = get_filters(offset=0, size=page_size)
    reports, total = await search_weaviate(
        filters=initial_filters,
        order_by=order_by,
        search_mode=ReportsSearchMode.SOURCES_ONLY,
    )
    if total > page_size:
        tasks = []
        for offset in range(page_size, total, page_size):
            filters = get_filters(offset=offset, size=page_size)
            tasks.append(
                search_weaviate(
                    filters=filters,
                    order_by=order_by,
                    search_mode=ReportsSearchMode.SOURCES_ONLY,
                )
            )
        # Submit tasks in batches
        for i in range(0, len(tasks), tasks_batch_size):
            logger.debug(
                f"Submitting tasks {i} to {i+tasks_batch_size} of {len(tasks)}"
            )
            results = await asyncio.gather(*tasks[i : i + tasks_batch_size])
            for reports_batch, _ in results:
                reports.extend(reports_batch)

    # Aggregate reports by date and source
    reports_by_date = {}
    for r in reports:
        date = DateTime.fromisoformat(r["data_report"]).date()
        source = r["id_source"]
        if date not in reports_by_date:
            reports_by_date[date] = {}
        if source not in reports_by_date[date]:
            reports_by_date[date][source] = 0
        reports_by_date[date][source] += 1

    reports = []

    for date, sources in reports_by_date.items():
        for source, count in sources.items():
            date: Date
            datetime_ = datetime(date.year, date.month, date.day)
            reports.append(
                ReportTimelineOut(data_report=datetime_, id_source=source, count=count)
            )

    # Sort reports by date and source
    reports = sorted(reports, key=lambda r: (r.data_report, r.id_source))

    return reports


@router_request(
    method="GET",
    router=router,
    path="/dashboard/top-subtypes",
    response_model=List[ReportTopSubtypesOut],
)
async def get_reports_dashboard_top_subtypes(
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
    keywords: List[str] = Query(None),
    latitude_min: float = None,
    latitude_max: float = None,
    longitude_min: float = None,
    longitude_max: float = None,
    order_by: ReportsOrderBy = ReportsOrderBy.TIMESTAMP_DESC,
    top_n: int = Query(5),
):
    def get_filters(offset: int, size: int) -> ReportFilters:
        return ReportFilters(
            limit=size,
            offset=offset,
            semantically_similar=semantically_similar,
            id_report=id_report,
            id_report_original=id_report_original,
            id_source_contains=id_source_contains,
            data_report_min=data_report_min,
            data_report_max=data_report_max,
            categoria_contains=categoria_contains,
            descricao_contains=descricao_contains,
            keywords=keywords,
            latitude_min=latitude_min if latitude_min else -90,
            latitude_max=latitude_max if latitude_max else 90,
            longitude_min=longitude_min if longitude_min else -180,
            longitude_max=longitude_max if longitude_max else 180,
        )

    # TODO: re-enable semantically similar search someday
    if semantically_similar:
        raise HTTPException(
            status_code=400,
            detail="Semantically similar search is disabled for now.",
        )
    page_size = 10000
    tasks_batch_size = 5
    initial_filters = get_filters(offset=0, size=page_size)
    reports, total = await search_weaviate(
        filters=initial_filters,
        order_by=order_by,
        search_mode=ReportsSearchMode.SUBTYPES_ONLY,
    )
    if total > page_size:
        tasks = []
        for offset in range(page_size, total, page_size):
            filters = get_filters(offset=offset, size=page_size)
            tasks.append(
                search_weaviate(
                    filters=filters,
                    order_by=order_by,
                    search_mode=ReportsSearchMode.SUBTYPES_ONLY,
                )
            )
        # Submit tasks in batches
        for i in range(0, len(tasks), tasks_batch_size):
            logger.debug(
                f"Submitting tasks {i} to {i+tasks_batch_size} of {len(tasks)}"
            )
            results = await asyncio.gather(*tasks[i : i + tasks_batch_size])
            for reports_batch, _ in results:
                reports.extend(reports_batch)

    # Aggregate reports by type and subtype
    reports_by_type_subtype = {}
    for r in reports:
        for tipo_subtipo in r["tipo_subtipo"]:
            tipo = tipo_subtipo["tipo"]
            for subtipo in tipo_subtipo["subtipo"]:
                key = hash(f"{tipo}{subtipo}")
                if key not in reports_by_type_subtype:
                    reports_by_type_subtype[key] = {
                        "tipo": tipo,
                        "subtipo": subtipo,
                        "count": 0,
                    }
                reports_by_type_subtype[key]["count"] += 1

    reports = [ReportTopSubtypesOut(**r) for r in reports_by_type_subtype.values()]

    # Sort reports by count
    reports = sorted(reports, key=lambda r: r.count, reverse=True)

    return reports[:top_n]


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
