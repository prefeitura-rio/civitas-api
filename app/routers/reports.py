import asyncio
from datetime import datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from loguru import logger
from pendulum import Date, DateTime

from app import config
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
    get_bigquery_client,
)
from google.cloud import bigquery

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
    id_source_contains: list[str] = Query(None),
    data_report_min: datetime = None,
    data_report_max: datetime = None,
    categoria_contains: list[str] = Query(None),
    descricao_contains: list[str] = Query(None),
    keywords: list[str] = Query(None),
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

    # Build BigQuery query with filters
    order_clause = (
        "ORDER BY data_report DESC"
        if order_by in [ReportsOrderBy.TIMESTAMP, ReportsOrderBy.TIMESTAMP_DESC]
        else "ORDER BY data_report ASC"
    )

    query = f"""
        WITH filtered_reports AS (
            SELECT
                id_report,
                id_source,
                id_report_original,
                data_report,
                orgaos,
                categoria,
                tipo_subtipo,
                descricao,
                logradouro,
                numero_logradouro,
                latitude,
                longitude,
                updated_at
            FROM `rj-civitas.integracao_reports.reports`
            WHERE 1=1
    """
    query_params = []

    if id_report:
        query += " AND id_report = @id_report"
        query_params.append(
            bigquery.ScalarQueryParameter("id_report", "STRING", id_report)
        )

    if id_report_original:
        query += " AND id_report_original = @id_report_original"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "id_report_original", "STRING", id_report_original
            )
        )

    if id_source_contains:
        query += " AND id_source IN UNNEST(@id_source_contains)"
        query_params.append(
            bigquery.ArrayQueryParameter(
                "id_source_contains", "STRING", id_source_contains
            )
        )

    if data_report_min:
        query += " AND data_report >= @data_report_min"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "data_report_min", "TIMESTAMP", data_report_min
            )
        )

    if data_report_max:
        query += " AND data_report <= @data_report_max"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "data_report_max", "TIMESTAMP", data_report_max
            )
        )

    if categoria_contains:
        query += " AND categoria IN UNNEST(@categoria_contains)"
        query_params.append(
            bigquery.ArrayQueryParameter(
                "categoria_contains", "STRING", categoria_contains
            )
        )

    if descricao_contains:
        conditions = []
        for i, desc in enumerate(descricao_contains):
            param_name = f"descricao_{i}"
            conditions.append(f"LOWER(descricao) LIKE LOWER(@{param_name})")
            query_params.append(
                bigquery.ScalarQueryParameter(param_name, "STRING", f"%{desc}%")
            )
        query += f" AND ({' OR '.join(conditions)})"

    if keywords:
        conditions = []
        for i, kw in enumerate(keywords):
            param_name = f"keyword_{i}"
            conditions.append(f"LOWER(descricao) LIKE LOWER(@{param_name})")
            query_params.append(
                bigquery.ScalarQueryParameter(param_name, "STRING", f"%{kw}%")
            )
        query += f" AND ({' OR '.join(conditions)})"

    if latitude_min is not None:
        query += " AND latitude >= @latitude_min"
        query_params.append(
            bigquery.ScalarQueryParameter("latitude_min", "FLOAT64", latitude_min)
        )

    if latitude_max is not None:
        query += " AND latitude <= @latitude_max"
        query_params.append(
            bigquery.ScalarQueryParameter("latitude_max", "FLOAT64", latitude_max)
        )

    if longitude_min is not None:
        query += " AND longitude >= @longitude_min"
        query_params.append(
            bigquery.ScalarQueryParameter("longitude_min", "FLOAT64", longitude_min)
        )

    if longitude_max is not None:
        query += " AND longitude <= @longitude_max"
        query_params.append(
            bigquery.ScalarQueryParameter("longitude_max", "FLOAT64", longitude_max)
        )

    query += f"""
        )
        SELECT *, (SELECT COUNT(*) FROM filtered_reports) AS total_count
        FROM filtered_reports
        {order_clause}
        LIMIT @limit OFFSET @offset
    """
    query_params.append(bigquery.ScalarQueryParameter("limit", "INT64", params.size))
    query_params.append(bigquery.ScalarQueryParameter("offset", "INT64", offset))

    # Execute BigQuery
    bq_client = get_bigquery_client()
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    query_job = bq_client.query(query, job_config=job_config)
    results = list(query_job.result())

    total = results[0]["total_count"] if results else 0
    reports = [ReportOut(**dict(row)) for row in results]

    return create_page(reports, params=params, total=total)


@router_request(
    method="GET",
    router=router,
    path="/categories",
    response_model=list[str],
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
    response_model=list[ReportLatLongOut],
)
async def get_reports_dashboard_map(
    user: Annotated[User, Depends(get_user)],
    request: Request,
    semantically_similar: str = None,
    id_report: str = None,
    id_report_original: str = None,
    id_source_contains: list[str] = Query(None),
    data_report_min: datetime = None,
    data_report_max: datetime = None,
    categoria_contains: list[str] = Query(None),
    descricao_contains: list[str] = Query(None),
    keywords: list[str] = Query(None),
    latitude_min: float = None,
    latitude_max: float = None,
    longitude_min: float = None,
    longitude_max: float = None,
    order_by: ReportsOrderBy = ReportsOrderBy.TIMESTAMP_DESC,
):
    # TODO: re-enable semantically similar search someday
    if semantically_similar:
        raise HTTPException(
            status_code=400,
            detail="Semantically similar search is disabled for now.",
        )

    # Build BigQuery query with filters
    query = f"""
        SELECT
            id_report,
            latitude,
            longitude
        FROM `rj-civitas.integracao_reports.reports`
        WHERE 1=1
    """
    query_params = []

    if id_report:
        query += " AND id_report = @id_report"
        query_params.append(
            bigquery.ScalarQueryParameter("id_report", "STRING", id_report)
        )

    if id_report_original:
        query += " AND id_report_original = @id_report_original"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "id_report_original", "STRING", id_report_original
            )
        )

    if id_source_contains:
        query += " AND id_source IN UNNEST(@id_source_contains)"
        query_params.append(
            bigquery.ArrayQueryParameter(
                "id_source_contains", "STRING", id_source_contains
            )
        )

    if data_report_min:
        query += " AND data_report >= @data_report_min"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "data_report_min", "TIMESTAMP", data_report_min
            )
        )

    if data_report_max:
        query += " AND data_report <= @data_report_max"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "data_report_max", "TIMESTAMP", data_report_max
            )
        )

    if categoria_contains:
        query += " AND categoria IN UNNEST(@categoria_contains)"
        query_params.append(
            bigquery.ArrayQueryParameter(
                "categoria_contains", "STRING", categoria_contains
            )
        )

    if descricao_contains:
        conditions = []
        for i, desc in enumerate(descricao_contains):
            param_name = f"descricao_{i}"
            conditions.append(f"LOWER(descricao) LIKE LOWER(@{param_name})")
            query_params.append(
                bigquery.ScalarQueryParameter(param_name, "STRING", f"%{desc}%")
            )
        query += f" AND ({' OR '.join(conditions)})"

    if keywords:
        conditions = []
        for i, kw in enumerate(keywords):
            param_name = f"keyword_{i}"
            conditions.append(f"LOWER(descricao) LIKE LOWER(@{param_name})")
            query_params.append(
                bigquery.ScalarQueryParameter(param_name, "STRING", f"%{kw}%")
            )
        query += f" AND ({' OR '.join(conditions)})"

    if latitude_min is not None:
        query += " AND latitude >= @latitude_min"
        query_params.append(
            bigquery.ScalarQueryParameter("latitude_min", "FLOAT64", latitude_min)
        )

    if latitude_max is not None:
        query += " AND latitude <= @latitude_max"
        query_params.append(
            bigquery.ScalarQueryParameter("latitude_max", "FLOAT64", latitude_max)
        )

    if longitude_min is not None:
        query += " AND longitude >= @longitude_min"
        query_params.append(
            bigquery.ScalarQueryParameter("longitude_min", "FLOAT64", longitude_min)
        )

    if longitude_max is not None:
        query += " AND longitude <= @longitude_max"
        query_params.append(
            bigquery.ScalarQueryParameter("longitude_max", "FLOAT64", longitude_max)
        )

    # Execute BigQuery
    bq_client = get_bigquery_client()
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    query_job = bq_client.query(query, job_config=job_config)
    results = query_job.result()

    reports = [ReportLatLongOut(**dict(row)) for row in results]

    return reports


@router_request(
    method="GET",
    router=router,
    path="/dashboard/timeline",
    response_model=list[ReportTimelineOut],
)
async def get_reports_dashboard_timeline(
    user: Annotated[User, Depends(get_user)],
    request: Request,
    semantically_similar: str = None,
    id_report: str = None,
    id_report_original: str = None,
    id_source_contains: list[str] = Query(None),
    data_report_min: datetime = None,
    data_report_max: datetime = None,
    categoria_contains: list[str] = Query(None),
    descricao_contains: list[str] = Query(None),
    keywords: list[str] = Query(None),
    latitude_min: float = None,
    latitude_max: float = None,
    longitude_min: float = None,
    longitude_max: float = None,
    order_by: ReportsOrderBy = ReportsOrderBy.TIMESTAMP_DESC,
):
    # TODO: re-enable semantically similar search someday
    if semantically_similar:
        raise HTTPException(
            status_code=400,
            detail="Semantically similar search is disabled for now.",
        )

    # Build BigQuery query with filters
    query = f"""
        SELECT
            DATE(data_report) AS data_report,
            id_source,
            COUNT(*) AS count
        FROM `rj-civitas.integracao_reports.reports`
        WHERE 1=1
    """
    query_params = []

    if id_report:
        query += " AND id_report = @id_report"
        query_params.append(
            bigquery.ScalarQueryParameter("id_report", "STRING", id_report)
        )

    if id_report_original:
        query += " AND id_report_original = @id_report_original"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "id_report_original", "STRING", id_report_original
            )
        )

    if id_source_contains:
        query += " AND id_source IN UNNEST(@id_source_contains)"
        query_params.append(
            bigquery.ArrayQueryParameter(
                "id_source_contains", "STRING", id_source_contains
            )
        )

    if data_report_min:
        query += f" AND data_report >= @data_report_min"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "data_report_min", "TIMESTAMP", data_report_min
            )
        )

    if data_report_max:
        query += f" AND data_report <= @data_report_max"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "data_report_max", "TIMESTAMP", data_report_max
            )
        )

    if categoria_contains:
        query += " AND categoria IN UNNEST(@categoria_contains)"
        query_params.append(
            bigquery.ArrayQueryParameter(
                "categoria_contains", "STRING", categoria_contains
            )
        )

    if descricao_contains:
        # Search for any of the keywords in descricao
        conditions = []
        for i, desc in enumerate(descricao_contains):
            param_name = f"descricao_{i}"
            conditions.append(f"LOWER(descricao) LIKE LOWER(@{param_name})")
            query_params.append(
                bigquery.ScalarQueryParameter(param_name, "STRING", f"%{desc}%")
            )
        query += f" AND ({' OR '.join(conditions)})"

    if keywords:
        # Search for any of the keywords in descricao
        conditions = []
        for i, kw in enumerate(keywords):
            param_name = f"keyword_{i}"
            conditions.append(f"LOWER(descricao) LIKE LOWER(@{param_name})")
            query_params.append(
                bigquery.ScalarQueryParameter(param_name, "STRING", f"%{kw}%")
            )
        query += f" AND ({' OR '.join(conditions)})"

    if latitude_min is not None:
        query += " AND latitude >= @latitude_min"
        query_params.append(
            bigquery.ScalarQueryParameter("latitude_min", "FLOAT64", latitude_min)
        )

    if latitude_max is not None:
        query += " AND latitude <= @latitude_max"
        query_params.append(
            bigquery.ScalarQueryParameter("latitude_max", "FLOAT64", latitude_max)
        )

    if longitude_min is not None:
        query += " AND longitude >= @longitude_min"
        query_params.append(
            bigquery.ScalarQueryParameter("longitude_min", "FLOAT64", longitude_min)
        )

    if longitude_max is not None:
        query += " AND longitude <= @longitude_max"
        query_params.append(
            bigquery.ScalarQueryParameter("longitude_max", "FLOAT64", longitude_max)
        )

    query += """
        GROUP BY data_report, id_source
        ORDER BY data_report, id_source
    """

    # Execute BigQuery
    bq_client = get_bigquery_client()
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    query_job = bq_client.query(query, job_config=job_config)
    results = query_job.result()

    reports = []
    for row in results:
        date = row["data_report"]
        datetime_ = datetime(date.year, date.month, date.day)
        reports.append(
            ReportTimelineOut(
                data_report=datetime_, id_source=row["id_source"], count=row["count"]
            )
        )

    return reports


@router_request(
    method="GET",
    router=router,
    path="/dashboard/top-subtypes",
    response_model=list[ReportTopSubtypesOut],
)
async def get_reports_dashboard_top_subtypes(
    user: Annotated[User, Depends(get_user)],
    request: Request,
    semantically_similar: str = None,
    id_report: str = None,
    id_report_original: str = None,
    id_source_contains: list[str] = Query(None),
    data_report_min: datetime = None,
    data_report_max: datetime = None,
    categoria_contains: list[str] = Query(None),
    descricao_contains: list[str] = Query(None),
    keywords: list[str] = Query(None),
    latitude_min: float = None,
    latitude_max: float = None,
    longitude_min: float = None,
    longitude_max: float = None,
    order_by: ReportsOrderBy = ReportsOrderBy.TIMESTAMP_DESC,
    top_n: int = Query(5),
):
    # TODO: re-enable semantically similar search someday
    if semantically_similar:
        raise HTTPException(
            status_code=400,
            detail="Semantically similar search is disabled for now.",
        )

    # Build BigQuery query with filters - aggregate by tipo/subtipo directly in SQL
    query = f"""
        WITH filtered_reports AS (
            SELECT tipo_subtipo
            FROM `rj-civitas.integracao_reports.reports`
            WHERE 1=1
    """
    query_params = []

    if id_report:
        query += " AND id_report = @id_report"
        query_params.append(
            bigquery.ScalarQueryParameter("id_report", "STRING", id_report)
        )

    if id_report_original:
        query += " AND id_report_original = @id_report_original"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "id_report_original", "STRING", id_report_original
            )
        )

    if id_source_contains:
        query += " AND id_source IN UNNEST(@id_source_contains)"
        query_params.append(
            bigquery.ArrayQueryParameter(
                "id_source_contains", "STRING", id_source_contains
            )
        )

    if data_report_min:
        query += " AND data_report >= @data_report_min"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "data_report_min", "TIMESTAMP", data_report_min
            )
        )

    if data_report_max:
        query += " AND data_report <= @data_report_max"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "data_report_max", "TIMESTAMP", data_report_max
            )
        )

    if categoria_contains:
        query += " AND categoria IN UNNEST(@categoria_contains)"
        query_params.append(
            bigquery.ArrayQueryParameter(
                "categoria_contains", "STRING", categoria_contains
            )
        )

    if descricao_contains:
        conditions = []
        for i, desc in enumerate(descricao_contains):
            param_name = f"descricao_{i}"
            conditions.append(f"LOWER(descricao) LIKE LOWER(@{param_name})")
            query_params.append(
                bigquery.ScalarQueryParameter(param_name, "STRING", f"%{desc}%")
            )
        query += f" AND ({' OR '.join(conditions)})"

    if keywords:
        conditions = []
        for i, kw in enumerate(keywords):
            param_name = f"keyword_{i}"
            conditions.append(f"LOWER(descricao) LIKE LOWER(@{param_name})")
            query_params.append(
                bigquery.ScalarQueryParameter(param_name, "STRING", f"%{kw}%")
            )
        query += f" AND ({' OR '.join(conditions)})"

    if latitude_min is not None:
        query += " AND latitude >= @latitude_min"
        query_params.append(
            bigquery.ScalarQueryParameter("latitude_min", "FLOAT64", latitude_min)
        )

    if latitude_max is not None:
        query += " AND latitude <= @latitude_max"
        query_params.append(
            bigquery.ScalarQueryParameter("latitude_max", "FLOAT64", latitude_max)
        )

    if longitude_min is not None:
        query += " AND longitude >= @longitude_min"
        query_params.append(
            bigquery.ScalarQueryParameter("longitude_min", "FLOAT64", longitude_min)
        )

    if longitude_max is not None:
        query += " AND longitude <= @longitude_max"
        query_params.append(
            bigquery.ScalarQueryParameter("longitude_max", "FLOAT64", longitude_max)
        )

    query += f"""
        )
        SELECT
            ts.tipo,
            subtipo,
            COUNT(*) AS count
        FROM filtered_reports,
            UNNEST(tipo_subtipo) AS ts,
            UNNEST(ts.subtipo) AS subtipo
        GROUP BY ts.tipo, subtipo
        ORDER BY count DESC
        LIMIT @top_n
    """
    query_params.append(bigquery.ScalarQueryParameter("top_n", "INT64", top_n))

    # Execute BigQuery
    bq_client = get_bigquery_client()
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    query_job = bq_client.query(query, job_config=job_config)
    results = query_job.result()

    reports = [ReportTopSubtypesOut(**dict(row)) for row in results]

    return reports


@router_request(
    method="GET",
    router=router,
    path="/sources",
    response_model=list[str],
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
    response_model=list[str],
)
async def get_report_subtypes(
    user: Annotated[User, Depends(get_user)],
    request: Request,
    type: list[str] = Query(None),
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
    response_model=list[str],
)
async def get_report_types(
    user: Annotated[User, Depends(get_user)],
    request: Request,
):
    metadata: ReportsMetadata | dict = await get_reports_metadata()
    if isinstance(metadata, dict):
        metadata = ReportsMetadata(**metadata)
    return metadata.distinct_types
