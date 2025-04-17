# -*- coding: utf-8 -*-
import asyncio
import base64
import re
import traceback
from contextlib import AbstractAsyncContextManager
from enum import Enum
from types import ModuleType
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import aiohttp
import orjson as json
import pendulum
import pytz
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi_cache.decorator import cache as cache_decorator
from google.cloud import bigquery
from google.cloud.bigquery.table import Row
from google.oauth2 import service_account
from httpx import AsyncClient
from loguru import logger
from pendulum import DateTime
from tortoise import Tortoise, connections
from tortoise.exceptions import DoesNotExist, IntegrityError

from app import config
from app.models import CompanyData, PersonData, PlateData
from app.pydantic_models import (
    CarPassageOut,
    CortexCompanyOut,
    CortexPersonOut,
    CortexPlacaOut,
    NPlatesBeforeAfterOut,
    RadarOut,
    ReportFilters,
    ReportsMetadata,
    WazeAlertOut,
)
from app.rate_limiter_cpf import cpf_limiter
from app.redis_cache import cache


class ReportsOrderBy(str, Enum):
    TIMESTAMP = (
        "timestamp"  # TODO: remove this later. this is kept for backward compatibility
    )
    TIMESTAMP_ASC = "timestamp_asc"
    TIMESTAMP_DESC = "timestamp_desc"
    DISTANCE = "distance"


class ReportsSearchMode(str, Enum):
    FULL = "full"
    LATLONG_ONLY = "latlong_only"
    SOURCES_ONLY = "sources_only"
    SUBTYPES_ONLY = "subtypes_only"


def build_get_car_by_radar_query(
    *,
    min_datetime: pendulum.DateTime,
    max_datetime: pendulum.DateTime,
    camera_numero: str,
    codcet: str = None,
    plate_hint: str = None,
) -> str:
    """
    Build a SQL query to fetch cars by radar within a time range.

    Args:
        min_datetime (pendulum.DateTime): The minimum datetime of the range.
        max_datetime (pendulum.DateTime): The maximum datetime of the range.
        camera_numero (str): The camera number.
        codcet (str, optional): The codcet. Defaults to None.
        plate_hint (str, optional): The plate hint. Defaults to None.

    Returns:
        str: The SQL query.
    """
    # Treat * as a single character wildcard by converting it to _
    plate_hint = plate_hint.upper().replace("*", "_") if plate_hint else None

    query = """
        SELECT DISTINCT
            placa,
            DATETIME(datahora, "America/Sao_Paulo") AS datahora,
            velocidade
        FROM `rj-cetrio.ocr_radar.readings_*`
        WHERE
            datahora >= TIMESTAMP("{{min_datetime}}", "America/Sao_Paulo")
            AND datahora <= TIMESTAMP("{{max_datetime}}", "America/Sao_Paulo")
    """.replace("{{min_datetime}}", min_datetime.to_datetime_string()).replace(
        "{{max_datetime}}", max_datetime.to_datetime_string()
    )

    if codcet:
        query += (
            f"AND (camera_numero = '{codcet}' OR camera_numero = '{camera_numero}')"
        )
    else:
        query += f"AND camera_numero = '{camera_numero}'"

    if plate_hint:
        query += f"AND placa LIKE '{plate_hint}'"

    return query


def generate_regular_filters(filters: ReportFilters) -> str:
    """
    Generate regular filters for the GraphQL query.

    Args:
        filters (ReportFilters): The report filters.

    Returns:
        str: The regular filters.
    """
    # Create regular filters
    base_regular_filters = """
        where: {
            operator: And,
            operands: [{{regular_filter_operands}}]
        },
    """
    regular_filter_operands = []
    if filters.id_report:
        regular_filter_operands.append(
            """
                {
                    path: ["id_report"],
                    operator: Equal,
                    valueText: "%s",
                }
            """
            % filters.id_report
        )
    if filters.id_report_original:
        regular_filter_operands.append(
            """
                {
                    path: ["id_report_original"],
                    operator: Equal,
                    valueText: "%s",
                }
            """
            % filters.id_report_original
        )
    if filters.id_source_contains:
        regular_filter_operands.append(
            """
                {
                    path: ["id_source"],
                    operator: ContainsAny,
                    valueText: %s,
                }
            """
            % filters.id_source_contains
        )
    if filters.data_report_min:
        timestamp_min = filters.data_report_min.replace(
            tzinfo=pytz.timezone(config.TIMEZONE)
        )
        regular_filter_operands.append(
            """
                {
                    path: ["%s"],
                    operator: GreaterThanEqual,
                    valueDate: "%s",
                }
            """
            % (
                config.EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN,
                timestamp_min.isoformat(),
            )
        )
    if filters.data_report_max:
        timestamp_max = filters.data_report_max.replace(
            tzinfo=pytz.timezone(config.TIMEZONE)
        )
        regular_filter_operands.append(
            """
                {
                    path: ["%s"],
                    operator: LessThanEqual,
                    valueDate: "%s",
                }
            """
            % (
                config.EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN,
                timestamp_max.isoformat(),
            )
        )
    if filters.categoria_contains:
        regular_filter_operands.append(
            """
                {
                    path: ["categoria"],
                    operator: ContainsAny,
                    valueText: %s,
                }
            """
            % filters.categoria_contains
        )
    if filters.descricao_contains:
        regular_filter_operands.append(
            """
                {
                    path: ["descricao"],
                    operator: ContainsAny,
                    valueText: %s,
                }
            """
            % filters.descricao_contains
        )
    if filters.keywords:
        regular_filter_operands.append(
            """
                {
                    path: ["report_data_raw"],
                    operator: ContainsAny,
                    valueText: %s,
                }
            """
            % filters.keywords
        )
    if filters.latitude_min:
        regular_filter_operands.append(
            """
                {
                    path: ["latitude"],
                    operator: GreaterThanEqual,
                    valueNumber: %s,
                }
            """
            % filters.latitude_min
        )
    if filters.latitude_max:
        regular_filter_operands.append(
            """
                {
                    path: ["latitude"],
                    operator: LessThanEqual,
                    valueNumber: %s,
                }
            """
            % filters.latitude_max
        )
    if filters.longitude_min:
        regular_filter_operands.append(
            """
                {
                    path: ["longitude"],
                    operator: GreaterThanEqual,
                    valueNumber: %s,
                }
            """
            % filters.longitude_min
        )
    if filters.longitude_max:
        regular_filter_operands.append(
            """
                {
                    path: ["longitude"],
                    operator: LessThanEqual,
                    valueNumber: %s,
                }
            """
            % filters.longitude_max
        )
    if regular_filter_operands:
        regular_filters = base_regular_filters.replace(
            "{{regular_filter_operands}}", ", ".join(regular_filter_operands)
        )
    else:
        regular_filters = ""

    return regular_filters


async def build_graphql_query(
    filters: ReportFilters, order_by: ReportsOrderBy, search_mode: ReportsSearchMode
) -> str:
    base_query = """
        {
            Aggregate {
                {{weaviate_schema_class}} (
                    {{regular_filters}}
                ) {
                    meta {
                        count
                    }
                }
            }
            Get {
                {{weaviate_schema_class}} (
                    {{pagination_filters}}
                    {{regular_filters}}
                    {{semantic_filter}}
                    {{sorting}}
                ) {
                    {{returned_attributes}}
                }
            }
        }
    """

    # Create pagination filter
    pagination_filters = f"limit: {filters.limit}\n offset: {filters.offset}"

    # Create semantic filter
    base_semantic_filter = """
        nearVector: {
            vector: %s,
        }
    """
    if filters.semantically_similar:
        vector = await generate_embeddings(filters.semantically_similar)
        semantic_filter = base_semantic_filter % vector
    else:
        semantic_filter = ""

    # Create sorting
    sorting = ""
    if order_by in [ReportsOrderBy.TIMESTAMP, ReportsOrderBy.TIMESTAMP_DESC]:
        sorting = (
            """
            sort: {
                path: "%s"
                order: desc
            }
        """
            % f"{config.EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN}_seconds"
        )
    elif order_by == ReportsOrderBy.TIMESTAMP_ASC:
        sorting = (
            """
            sort: {
                path: "%s"
                order: asc
            }
        """
            % f"{config.EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN}_seconds"
        )

    # Set returned attributes
    if search_mode == ReportsSearchMode.FULL:
        returned_attributes = """
                    id_report
                    id_source
                    id_report_original
                    data_report
                    orgaos
                    categoria
                    tipo_subtipo {
                        tipo
                        subtipo
                    }
                    descricao
                    logradouro
                    numero_logradouro
                    latitude
                    longitude
                    _additional {
                        certainty
                    }
        """
    elif search_mode == ReportsSearchMode.LATLONG_ONLY:
        returned_attributes = """
                    id_report
                    latitude
                    longitude
        """
    elif search_mode == ReportsSearchMode.SOURCES_ONLY:
        returned_attributes = """
                    data_report
                    id_source
        """
    elif search_mode == ReportsSearchMode.SUBTYPES_ONLY:
        returned_attributes = """
                    tipo_subtipo {
                        tipo
                        subtipo
                    }
        """
    else:
        raise ValueError("Invalid search mode")

    # Build query
    query = base_query.replace("{{pagination_filters}}", pagination_filters)
    query = query.replace("{{regular_filters}}", generate_regular_filters(filters))
    query = query.replace("{{semantic_filter}}", semantic_filter)
    query = query.replace("{{sorting}}", sorting)
    query = query.replace("{{weaviate_schema_class}}", config.WEAVIATE_SCHEMA_CLASS)
    query = query.replace("{{returned_attributes}}", returned_attributes)
    query = query.replace("'", '"')

    return query


def build_hint_query(
    placa: str,
    min_datetime: pendulum.DateTime,
    max_datetime: pendulum.DateTime,
    latitude_min: float = None,
    latitude_max: float = None,
    longitude_min: float = None,
    longitude_max: float = None,
) -> str:
    """
    Build a SQL query to fetch plate hints within a time range.

    Args:
        placa (str): The vehicle license plate.
        min_datetime (pendulum.DateTime): The minimum datetime of the range.
        max_datetime (pendulum.DateTime): The maximum datetime of the range.
        latitude_min (float): The minimum latitude.
        latitude_max (float): The maximum latitude.
        longitude_min (float): The minimum longitude.
        longitude_max (float): The maximum longitude.

    Returns:
        str: The SQL query.
    """

    # Treat * as a single character wildcard by converting it to _
    placa = placa.upper().replace("*", "_")

    query = """
        SELECT
            placa
        FROM `rj-cetrio.ocr_radar.readings_*`
        WHERE
            placa LIKE '{{placa}}'
    """.replace("{{placa}}", placa)

    if latitude_min and latitude_max:
        query += """
            AND (camera_latitude BETWEEN {{latitude_min}} AND {{latitude_max}})
        """.replace("{{latitude_min}}", str(latitude_min)).replace(
            "{{latitude_max}}", str(latitude_max)
        )

    if longitude_min and longitude_max:
        query += """
            AND (camera_longitude BETWEEN {{longitude_min}} AND {{longitude_max}})
        """.replace("{{longitude_min}}", str(longitude_min)).replace(
            "{{longitude_max}}", str(longitude_max)
        )

    query += """
            AND DATETIME(datahora, "America/Sao_Paulo") >= DATETIME("{{min_datetime}}")
            AND DATETIME(datahora, "America/Sao_Paulo") <= DATETIME("{{max_datetime}}")
        GROUP BY placa
    """.replace("{{min_datetime}}", min_datetime.to_datetime_string()).replace(
        "{{max_datetime}}", max_datetime.to_datetime_string()
    )

    return query


def build_n_plates_query(
    placa: str,
    min_datetime: pendulum.DateTime,
    max_datetime: pendulum.DateTime,
    n_minutes: int,
    n_plates: int,
) -> Tuple[str, List[bigquery.ScalarQueryParameter]]:
    """
    Build a SQL query to fetch N plates before and after a plate within a time range.

    Args:
        placa (str): The vehicle license plate.
        min_datetime (pendulum.DateTime): The minimum datetime of the range.
        max_datetime (pendulum.DateTime): The maximum datetime of the range.
        n_minutes (int): The number of minutes before and after.
        n_plates (int): The number of plates before and after.

    Returns:
        Tuple[str, List[bigquery.ScalarQueryParameter]]: The SQL query and the query parameters.
    """
    try:
        min_datetime = min_datetime.in_tz(config.TIMEZONE)
        max_datetime = max_datetime.in_tz(config.TIMEZONE)
    except ValueError:
        raise ValueError("Invalid datetime range")
    query = """
    -- Select all radar readings
    WITH all_readings AS (
        SELECT
            placa,
            velocidade,
            DATETIME(datahora, 'America/Sao_Paulo') AS datahora_local,
            camera_numero,
            empresa,
            camera_latitude AS latitude,
            camera_longitude AS longitude,
            DATETIME(datahora_captura, 'America/Sao_Paulo') AS datahora_captura,
            ROW_NUMBER() OVER (PARTITION BY placa, datahora ORDER BY datahora) AS row_num_duplicate
        FROM `rj-cetrio.ocr_radar.readings_*`
        WHERE
            DATETIME(datahora, "America/Sao_Paulo")
            BETWEEN DATETIME(DATETIME_SUB(@start_datetime, INTERVAL 1 DAY), "America/Sao_Paulo")
            AND DATETIME(DATETIME_ADD(@end_datetime, INTERVAL 1 DAY), "America/Sao_Paulo")
        QUALIFY(row_num_duplicate) = 1
    ),

    -- Get all unique locations and associated information
    unique_locations AS (
        SELECT
            t1.codcet,
            t2.camera_numero,
            t1.bairro,
            CAST(t1.latitude AS FLOAT64) AS latitude,
            CAST(t1.longitude AS FLOAT64) AS longitude,
            TRIM(
            REGEXP_REPLACE(
                REGEXP_REPLACE(t1.locequip, r'^(.*?) -.*', r'\\1'), -- Remove the part after " -"
                r'\s+', ' ') -- Remove extra spaces
            ) AS locequip,
            COALESCE(CONCAT(' - SENTIDO ', sentido), '') AS sentido,
            TO_BASE64(
                MD5(
                    CONCAT(
                        LEFT(t1.codcet, LENGTH(t1.codcet) -1),
                        COALESCE(t1.sentido, '') -- Combine codcet and sentido, omitting the last character of codcet
                    )
                )
            ) AS hashed_coordinates, -- Generate a unique hash for the location
        FROM `rj-cetrio.ocr_radar.equipamento` t1
        JOIN `rj-cetrio.ocr_radar.equipamento_codcet_to_camera_numero` t2
            ON t1.codcet = t2.codcet
    ),

    -- Select unique coordinates for each location
    unique_location_coordinates  AS (
        SELECT
            hashed_coordinates,
            locequip,
            ROW_NUMBER() OVER(PARTITION BY hashed_coordinates) rn
        FROM unique_locations
        QUALIFY(rn) = 1
    ),

    -- Group radar information with readings
    radar_group AS (
        SELECT
            l.camera_numero,
            l.codcet,
            l.bairro,
            l.latitude,
            l.longitude,
            b.locequip,
            l.sentido,
            l.hashed_coordinates
        FROM
            unique_locations l
            JOIN unique_location_coordinates  b ON l.hashed_coordinates = b.hashed_coordinates
        WHERE
            -- Ensure there is at least one reading for each radar
            EXISTS (
                SELECT
                    1
                FROM
                    all_readings c
                WHERE l.camera_numero = c.camera_numero
            )
    ),

    -- Select specific readings for the desired license plate
    selected_readings AS (
        SELECT
            b.hashed_coordinates,
            a.placa,
            a.velocidade,
            a.datahora_local,
            a.camera_numero,
            a.empresa,
            a.latitude,
            a.longitude,
            a.datahora_captura,
            ROW_NUMBER() OVER(PARTITION BY a.placa ORDER BY a.datahora_local) n_deteccao,
            DATETIME_SUB(a.datahora_local, INTERVAL @N_minutes MINUTE) AS datahora_inicio,
            DATETIME_ADD(a.datahora_local, INTERVAL @N_minutes MINUTE) AS datahora_fim
        FROM all_readings a
        JOIN radar_group b ON a.camera_numero = b.camera_numero
        WHERE
            a.placa = @plate
            AND datahora_local
            BETWEEN DATETIME(@start_datetime, "America/Sao_Paulo")
            AND DATETIME(@end_datetime, "America/Sao_Paulo")
    ),

    -- Look for records before and after the selected_readings reading time
    before_and_after AS (
        SELECT
            l.codcet,
            l.hashed_coordinates,
            l.locequip,
            l.bairro,
            l.sentido,
            a.*,
            s.n_deteccao
        FROM
            all_readings a
        JOIN radar_group l ON a.camera_numero = l.camera_numero
        JOIN selected_readings s ON l.hashed_coordinates = s.hashed_coordinates
            AND (
                a.datahora_local BETWEEN
                    s.datahora_inicio AND s.datahora_fim
            )
    ),

    -- Aggregate final results
    aggregations AS (
        SELECT
            b.n_deteccao AS id_detection,
            s.datahora_local AS detection_time, -- group by each plate detection
            b.hashed_coordinates AS id_camera_groups,
            ARRAY(
                SELECT
                    g.camera_numero
                FROM
                    radar_group g
                WHERE g.hashed_coordinates = b.hashed_coordinates
            ) AS radars,
            CONCAT(b.locequip, b.sentido, ' - ', b.bairro) AS location,
            b.latitude AS latitude,
            b.longitude AS longitude,
            ARRAY_AGG(
                STRUCT(
                    b.datahora_local AS `timestamp`,
                    b.placa,
                    b.camera_numero,
                    RIGHT(b.codcet, 1) AS lane,
                    b.velocidade AS speed
                )
                ORDER BY
                    b.datahora_local) as detections -- Organize detections by date/time
        FROM before_and_after b
        JOIN selected_readings s ON b.hashed_coordinates = s.hashed_coordinates AND b.n_deteccao = s.n_deteccao
        GROUP BY all
    ),

    -- Order detection results
    detection_orders AS (
        SELECT
            a.id_detection,
            a.id_camera_groups,
            a.radars,
            a.detection_time,
            a.location,
            a.latitude,
            a.longitude,
            d.*,
            ROW_NUMBER() OVER(PARTITION BY a.id_detection ORDER BY d.timestamp) AS detection_order
        FROM
            aggregations a
            JOIN UNNEST(a.detections) d
    ),

    -- Select the specific detection orders for the target plate
    selected_orders AS (
        SELECT
            id_detection,
            detection_order
        FROM
        -- Order detection results
            detection_orders
        WHERE
            placa = @plate
    ),

    -- Final query to aggregate results
    final_results AS (
        SELECT
            a.id_detection,
            a.id_camera_groups,
            a.radars,
            a.detection_time,
            DATETIME_SUB(a.detection_time, INTERVAL @N_minutes MINUTE) AS start_time,
            DATETIME_ADD(a.detection_time, INTERVAL @N_minutes MINUTE) AS end_time,
            a.location,
            a.latitude,
            a.longitude,
            a.timestamp,
            a.placa AS plate,
            a.camera_numero,
            a.lane,
            a.speed,
            COUNT(a.placa) AS `count`
        FROM
        -- Order detection results
            detection_orders a
        JOIN
            selected_orders b
        ON
            a.id_detection = b.id_detection
        WHERE
            a.detection_order BETWEEN b.detection_order - @N_plates AND b.detection_order + @N_plates
        GROUP BY ALL
    ),

    -- Count plates in the final results
    plates_count AS  (
        SELECT
            plate,
            COUNT(plate) AS `count`
        FROM
            final_results
        GROUP BY ALL
    ),

    -- Final aggregation of results into an array
    final_array_agg AS (
        SELECT
            a.id_detection,
            a.id_camera_groups,
            a.radars,
            a.detection_time,
            a.start_time,
            a.end_time,
            a.location,
            a.latitude,
            a.longitude,
            ARRAY_AGG(
            STRUCT(
                a.timestamp,
                a.plate,
                a.camera_numero,
                a.lane,
                a.speed,
                b.count
            )
            ORDER BY a.timestamp
            ) AS detections
        FROM
            final_results a
        JOIN
            plates_count b
        ON a.plate = b.plate
        GROUP BY ALL
    )

    -- Final selection to retrieve results
    SELECT
        id_camera_groups,
        radars,
        detection_time,
        start_time,
        end_time,
        location,
        latitude,
        longitude,
        ARRAY_LENGTH(detections) AS total_detections,
        detections
    FROM
        final_array_agg
    """
    query_params = [
        bigquery.ScalarQueryParameter("plate", "STRING", placa),
        bigquery.ScalarQueryParameter("start_datetime", "TIMESTAMP", min_datetime),
        bigquery.ScalarQueryParameter("end_datetime", "TIMESTAMP", max_datetime),
        bigquery.ScalarQueryParameter("N_minutes", "INT64", n_minutes),
        bigquery.ScalarQueryParameter("N_plates", "INT64", n_plates),
    ]
    return query, query_params


def build_positions_query(
    placa: str,
    min_datetime: pendulum.DateTime,
    max_datetime: pendulum.DateTime,
    min_distance: float = 0,
) -> str:
    """
    Build a SQL query to fetch the positions of a vehicle within a time range.

    Args:
        placa (str): The vehicle license plate.
        min_datetime (pendulum.DateTime): The minimum datetime of the range.
        max_datetime (pendulum.DateTime): The maximum datetime of the range.
        min_distance (float, optional): The minimum distance between plates. Defaults to 0.

    Returns:
        str: The SQL query.
    """

    try:
        min_datetime = min_datetime.in_tz(config.TIMEZONE)
        max_datetime = max_datetime.in_tz(config.TIMEZONE)
    except ValueError:
        raise ValueError("Invalid datetime range")

    query = (
        """
        WITH ordered_positions AS (
            SELECT
                DISTINCT
                    DATETIME(datahora, "America/Sao_Paulo") AS datahora,
                    placa,
                    camera_numero,
                    camera_latitude,
                    camera_longitude,
                    velocidade
            FROM `rj-cetrio.ocr_radar.readings_*`
            WHERE
                `rj-cetrio`.ocr_radar.plateDistance(TRIM(UPPER(REGEXP_REPLACE(NORMALIZE(
                    placa, NFD), r'\pM', ''))), "{{placa}}") <= 0.0
                AND (camera_latitude != 0 AND camera_longitude != 0)
                AND DATETIME(datahora, "America/Sao_Paulo") >= DATETIME("{{min_datetime}}")
                AND DATETIME(datahora, "America/Sao_Paulo") <= DATETIME("{{max_datetime}}")
            ORDER BY datahora ASC, placa ASC
        ),

        loc AS (
            SELECT
                t2.camera_numero,
                t1.bairro,
                t1.locequip AS localidade,
                CAST(t1.latitude AS FLOAT64) AS latitude,
                CAST(t1.longitude AS FLOAT64) AS longitude,
            FROM `rj-cetrio.ocr_radar_staging.equipamento` t1
            JOIN `rj-cetrio.ocr_radar.equipamento_codcet_to_camera_numero` t2
                ON t1.codcet = t2.codcet
        )

        SELECT
            p.datahora,
            p.camera_numero,
            COALESCE(l.latitude, p.camera_latitude) AS latitude,
            COALESCE(l.longitude, p.camera_longitude) AS longitude,
            l.bairro,
            l.localidade,
            p.velocidade
        FROM ordered_positions p
        LEFT JOIN loc l ON p.camera_numero = l.camera_numero
        ORDER BY p.datahora ASC
        """.replace("{{placa}}", placa)
        .replace("{{min_datetime}}", min_datetime.to_datetime_string())
        .replace("{{max_datetime}}", max_datetime.to_datetime_string())
        .replace("{{min_distance}}", str(min_distance))
    )

    return query


async def cortex_request(
    method: str,
    url: str,
    cpf: str,
    raise_for_status: bool = True,
    **kwargs: Any,
) -> Tuple[bool, Any]:
    """
    Make a request to the Cortex API.

    Args:
        method (str): The HTTP method.
        url (str): The URL.
        **kwargs (Any): The keyword arguments.

    Returns:
        Tuple[bool, Any]: Whether the request was a success and the response
    """
    # Check whether the CPF is allowed to make the request
    if not await cpf_limiter.check(cpf):
        raise HTTPException(
            status_code=429,
            detail="Rate limit for this CPF exceeded Cortex limits. Try again later.",
        )

    # Get the Cortex token
    token = await cache.get_cortex_token()

    # Setup headers
    headers = kwargs.get("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    headers["usuario"] = cpf

    # Actually make the request
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers, **kwargs) as response:
            if raise_for_status:
                response.raise_for_status()
            elif response.status != 200:
                return False, response
            return True, await response.json()


async def get_company_details(cnpj: str, cpf: str) -> CortexCompanyOut:
    # Check if we already have this company in our database
    company_data = await CompanyData.get_or_none(cnpj=cnpj)

    # If we do, return it
    if company_data:
        logger.debug(f"Found CNPJ {cnpj} in our database. Returning cached data.")
        return CortexCompanyOut(
            **company_data.data,
            created_at=company_data.created_at,
            updated_at=company_data.updated_at,
        )

    # If we don't, try to fetch it from Cortex
    logger.debug(f"CNPJ {cnpj} not found in our database. Fetching data from Cortex.")
    success, data = await cortex_request(
        method="GET",
        url=f"{config.CORTEX_PESSOAS_BASE_URL}/pessoajuridica/{cnpj}",
        cpf=cpf,
        raise_for_status=False,
    )
    if not success:
        if isinstance(data, aiohttp.ClientResponse):
            logger.debug(f"Failed to fetch data from Cortex for CNPJ {cnpj}.")
            logger.debug(f"Status: {data.status}")
            if data.status == 451:
                raise HTTPException(
                    status_code=451,
                    detail="Unavailable for legal reasons. CPF might be blocked.",
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Something unexpected happened to Cortex API",
                )
        else:
            raise HTTPException(
                status_code=500, detail="Something unexpected happened to Cortex API"
            )

    # Save the data to our database
    company_data = await CompanyData.create(cnpj=cnpj, data=data)
    return CortexCompanyOut(
        **data, created_at=company_data.created_at, updated_at=company_data.updated_at
    )


async def get_person_details(lookup_cpf: str, cpf: str) -> CortexPersonOut:
    # Check if we already have this person in our database
    person_data = await PersonData.get_or_none(cpf=lookup_cpf)

    # If we do, return it
    if person_data:
        logger.debug(f"Found CPF {lookup_cpf} in our database. Returning cached data.")
        return CortexPersonOut(
            **person_data.data,
            created_at=person_data.created_at,
            updated_at=person_data.updated_at,
        )

    # If we don't, try to fetch it from Cortex
    logger.debug(
        f"CPF {lookup_cpf} not found in our database. Fetching data from Cortex."
    )
    success, data = await cortex_request(
        method="GET",
        url=f"{config.CORTEX_PESSOAS_BASE_URL}/pessoafisica/{lookup_cpf}",
        cpf=cpf,
        raise_for_status=False,
    )
    if not success:
        if isinstance(data, aiohttp.ClientResponse):
            logger.debug(f"Failed to fetch data from Cortex for CPF {lookup_cpf}.")
            logger.debug(f"Status: {data.status}")
            if data.status == 451:
                raise HTTPException(
                    status_code=451,
                    detail="Unavailable for legal reasons. CPF might be blocked.",
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Something unexpected happened to Cortex API",
                )
        else:
            raise HTTPException(
                status_code=500, detail="Something unexpected happened to Cortex API"
            )

    # Save the data to our database
    person_data = await PersonData.create(cpf=lookup_cpf, data=data)
    return CortexPersonOut(
        **data, created_at=person_data.created_at, updated_at=person_data.updated_at
    )


async def get_plate_details(
    plate: str, cpf: str, raise_for_errors: bool = True
) -> CortexPlacaOut | None:
    # Check if we already have this plate in our database
    plate_data = await PlateData.get_or_none(plate=plate)

    # If we do, return it
    if plate_data:
        logger.debug(f"Found plate {plate} in our database. Returning cached data.")
        return CortexPlacaOut(
            **plate_data.data,
            created_at=plate_data.created_at,
            updated_at=plate_data.updated_at,
        )

    # If we don't, try to fetch it from Cortex
    logger.debug(f"Plate {plate} not found in our database. Fetching data from Cortex.")
    success, data = await cortex_request(
        method="GET",
        url=f"{config.CORTEX_VEICULOS_BASE_URL}/emplacamentos/placa/{plate}",
        cpf=cpf,
        raise_for_status=False,
    )
    if not success:
        if isinstance(data, aiohttp.ClientResponse):
            if data.status == 451:
                if raise_for_errors:
                    raise HTTPException(
                        status_code=451,
                        detail="Unavailable for legal reasons. CPF might be blocked.",
                    )
                return None
            else:
                if raise_for_errors:
                    raise HTTPException(
                        status_code=500,
                        detail="Something unexpected happened to Cortex API",
                    )
                return None
        else:
            if raise_for_errors:
                raise HTTPException(
                    status_code=500,
                    detail="Something unexpected happened to Cortex API",
                )
            return None

    # Save the data to our database
    plate_data = await PlateData.create(plate=plate, data=data)
    return CortexPlacaOut(
        **data, created_at=plate_data.created_at, updated_at=plate_data.updated_at
    )


def get_bigquery_client() -> bigquery.Client:
    """Get the BigQuery client.

    Returns:
        bigquery.Client: The BigQuery client.
    """
    credentials = get_gcp_credentials()
    return bigquery.Client(credentials=credentials, project=credentials.project_id)


def get_gcp_credentials(scopes: List[str] = None) -> service_account.Credentials:
    """Get the GCP credentials.

    Args:
        scopes (List[str], optional): The scopes to use. Defaults to None.

    Returns:
        service_account.Credentials: The GCP credentials.
    """
    info: dict = json.loads(base64.b64decode(config.GCP_SERVICE_ACCOUNT_CREDENTIALS))
    creds = service_account.Credentials.from_service_account_info(info)
    if scopes:
        creds = creds.with_scopes(scopes)
    return creds


def check_schema_equality(dict1: dict, dict2: dict) -> bool:
    """
    Check if two dictionaries are equal.

    Args:
        dict1 (dict): The first dictionary.
        dict2 (dict): The second dictionary.

    Returns:
        bool: True if the dictionaries are equal, False otherwise.
    """
    for k, v in dict1.items():
        if isinstance(v, dict):
            if not check_schema_equality(v, dict2[k]):
                return False
        elif isinstance(v, list):
            for i in range(len(v)):
                if isinstance(v[i], dict):
                    if not check_schema_equality(v[i], dict2[k][i]):
                        return False
                elif v[i] != dict2[k][i]:
                    return False
        elif v != dict2[k]:
            return False
    return True


def create_update_weaviate_schema():
    """
    Create or update the Weaviate schema.
    """
    schema = config.WEAVIATE_SCHEMA
    # Check if class name already exists
    response = requests.get(
        f"{config.WEAVIATE_BASE_URL}/v1/schema/{schema['class']}", timeout=10
    )
    if response.status_code == 200:
        # Check if the schema is the same
        existing_schema = response.json()
        if not check_schema_equality(schema, existing_schema):
            # Update schema
            # TODO: Failed to update schema: b'{"error":[{"message":"updating schema:
            # TYPE_UPDATE_CLASS: bad request :parse class update: properties cannot be updated
            # through updating the class. Use the add property feature (e.g.
            # \\"POST /v1/schema/{className}/properties\\") to add additional properties"}]}\n'
            # response = requests.put(
            #     f"{config.WEAVIATE_BASE_URL}/v1/schema/{schema['class']}", json=schema, timeout=10
            # )
            # if response.status_code != 200:
            #     logger.error(f"Failed to update schema: {response.content}")
            # else:
            #     logger.info(f"Schema updated: {response.content}")
            logger.warning("Schema updating is not yet implemented")
        else:
            logger.info("Schema is up to date")
    else:
        # Create schema
        response = requests.post(
            f"{config.WEAVIATE_BASE_URL}/v1/schema", json=schema, timeout=10
        )
        if response.status_code != 200:
            logger.error(f"Failed to create schema: {response.content}")
        else:
            logger.info(f"Schema created: {response.content}")


def chunk_locations(locations, N):
    if N >= len(locations) or N == 1:
        return [locations]

    chunks = []
    i = 0
    while i < len(locations):
        if i + N <= len(locations):
            chunk = locations[i : i + N]
            chunks.append(chunk)
            i += N - 1
        else:
            chunk = locations[i:]
            chunks.append(chunk)
            break
    return chunks


async def generate_embeddings(text: str) -> List[float]:
    """
    Generate embeddings for a text.

    Args:
        text (str): The text.

    Returns:
        List[float]: The embeddings.
    """
    # TODO: This is a temporary placeholder for the actual implementation
    return [0.0] * 256
    # async with aiohttp.ClientSession() as session:
    #     async with session.post(
    #         f"{config.EMBEDDING_API_BASE_URL}/embed/",
    #         json={"text": text},
    #     ) as response:
    #         response.raise_for_status()
    #         data = await response.json()
    #         return data["embedding"]


async def generate_embeddings_batch(
    texts: List[str], batch_size: int = None
) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts.

    Args:
        texts (List[str]): The texts.
        batch_size (int, optional): The batch size. Defaults to None.

    Returns:
        List[List[float]]: The embeddings.
    """
    # TODO: This is a temporary placeholder for the actual implementation
    return [[0.0] * 256 for _ in texts]
    # async with aiohttp.ClientSession() as session:
    #     if not batch_size:
    #         async with session.post(
    #             f"{config.EMBEDDING_API_BASE_URL}/embed/batch/",
    #             json={"texts": texts},
    #         ) as response:
    #             response.raise_for_status()
    #             data = await response.json()
    #             return data["embeddings"]
    #     embeddings = []
    #     for i in range(0, len(texts), batch_size):
    #         batch = texts[i : i + batch_size]
    #         async with session.post(
    #             f"{config.EMBEDDING_API_BASE_URL}/embed/batch/",
    #             json={"texts": batch},
    #         ) as response:
    #             response.raise_for_status()
    #             data = await response.json()
    #             embeddings.extend(data["embeddings"])
    #     return embeddings


@cache_decorator(expire=config.CACHE_CAR_BY_RADAR_TTL)
def get_car_by_radar(
    min_datetime: pendulum.DateTime,
    max_datetime: pendulum.DateTime,
    camera_numero: str,
    codcet: str = None,
    plate_hint: str = None,
) -> List[CarPassageOut]:
    """
    Fetch cars by radar within a time range.

    Args:
        min_datetime (pendulum.DateTime): The minimum datetime of the range.
        max_datetime (pendulum.DateTime): The maximum datetime of the range.
        camera_numero (str): The camera number.
        codcet (str, optional): The codcet. Defaults to None.
        plate_hint (str, optional): The plate hint. Defaults to None.

    Returns:
        List[CarPassageOut]: The car passages.
    """
    query = build_get_car_by_radar_query(
        min_datetime=min_datetime,
        max_datetime=max_datetime,
        camera_numero=camera_numero,
        codcet=codcet,
        plate_hint=plate_hint,
    )
    bq_client = get_bigquery_client()
    query_job = bq_client.query(query)
    data = query_job.result(page_size=config.GOOGLE_BIGQUERY_PAGE_SIZE)
    car_passages = []
    for page in data.pages:
        for row in page:
            row: Row
            row_data = dict(row.items())
            placa = row_data["placa"]
            datahora = row_data["datahora"]
            velocidade = row_data["velocidade"]
            car_passages.append(
                CarPassageOut(plate=placa, timestamp=datahora, speed=velocidade)
            )
    # Sort car passages by timestamp ascending
    car_passages = sorted(car_passages, key=lambda x: x.timestamp)
    return car_passages


@cache_decorator(expire=config.CACHE_FOGOCRUZADO_TTL)
async def get_fogocruzado_reports() -> List[dict]:
    """
    Fetch reports from Fogo Cruzado API.

    Returns:
        List[dict]: The Fogocruzado reports.
    """

    async def get_url(url, url_parameters, token):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=url_parameters,
                headers={"Authorization": f"Bearer {token}"},
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data

    token = await cache.get_fogocruzado_token()
    url = f"{config.FOGOCRUZADO_BASE_URL}/api/v2/occurrences"
    url_parameters = {
        "idCities": "d1bf56cc-6d85-4e6a-a5f5-0ab3f4074be3",  # Rio de Janeiro
        "idState": "b112ffbe-17b3-4ad0-8f2a-2038745d1d14",  # Rio de Janeiro
        "initialdate": pendulum.now()
        .subtract(days=1)
        .to_date_string(),  # Today's + yesterday's
        "page": 1,  # Page number
    }
    data = await get_url(url, url_parameters, token)
    page_count = data["pageMeta"]["pageCount"]
    reports = data["data"]
    awaitables = []
    for page in range(2, page_count + 1):
        url_parameters["page"] = page
        awaitables.append(get_url(url, url_parameters, token))
    additional_data = await asyncio.gather(*awaitables)
    for data in additional_data:
        reports += data["data"]
    for report in reports:
        if report["latitude"]:
            report["latitude"] = float(report["latitude"])
        if report["longitude"]:
            report["longitude"] = float(report["longitude"])
    return reports


def get_trips_chunks(locations, max_time_interval):
    for point in locations:
        point["datetime"] = point["datahora"]

    chunks = []
    if len(locations) == 0:
        return chunks
    current_chunk = [locations[0]]

    for i in range(1, len(locations)):
        point_anterior = locations[i - 1]
        point_atual = locations[i]

        diferenca_tempo = (
            point_atual["datetime"] - point_anterior["datetime"]
        ).total_seconds()
        point_anterior["seconds_to_next_point"] = diferenca_tempo
        if diferenca_tempo > max_time_interval:
            point_anterior["seconds_to_next_point"] = None
            chunks.append(current_chunk)
            current_chunk = [point_atual]
        else:
            current_chunk.append(point_atual)

    current_chunk[-1]["seconds_to_next_point"] = (
        None  # Ensure the last point in the final chunk has None
    )
    chunks.append(current_chunk)

    for chunk in chunks:
        for point in chunk:
            point.pop("datetime")

    return chunks


@cache_decorator(expire=config.CACHE_CAR_PATH_TTL)
async def get_path(
    placa: str,
    min_datetime: pendulum.DateTime,
    max_datetime: pendulum.DateTime,
    max_time_interval: int = 60 * 60,
    polyline: bool = False,
    min_plate_distance: float = 0,
) -> List[Dict[str, Union[str, List]]]:
    locations_interval = (
        await get_positions(
            placa, min_datetime, max_datetime, min_plate_distance=min_plate_distance
        )
    )["locations"]
    locations_trips_original = get_trips_chunks(
        locations=locations_interval, max_time_interval=max_time_interval
    )

    final_paths = []
    for locations in locations_trips_original:
        locations_trips = []
        polyline_trips = []
        locations_chunks = chunk_locations(
            locations=locations, N=config.GOOGLE_MAPS_API_MAX_POINTS_PER_REQUEST
        )
        for location_chunk in locations_chunks:
            locations_trips.append(location_chunk)
            if polyline:
                route = await get_route_path(locations=location_chunk)
                polyline_trips.append(route)
        final_paths.append(
            {
                "locations": locations_trips,
                "polyline": polyline_trips if polyline else None,
            }
        )

    return final_paths


@cache_decorator(expire=config.CACHE_CAR_HINTS_TTL)
async def get_hints(
    placa: str,
    min_datetime: pendulum.DateTime,
    max_datetime: pendulum.DateTime,
    latitude_min: float = None,
    latitude_max: float = None,
    longitude_min: float = None,
    longitude_max: float = None,
) -> List[str]:
    """
    Fetch plate hints within a time range.

    Args:
        placa (str): The vehicle license plate.
        min_datetime (pendulum.DateTime): The minimum datetime of the range.
        max_datetime (pendulum.DateTime): The maximum datetime of the range.
        latitude_min (float): The minimum latitude.
        latitude_max (float): The maximum latitude.
        longitude_min (float): The minimum longitude.
        longitude_max (float): The maximum longitude.

    Returns:
        List[str]: The plate hints.
    """
    query = build_hint_query(
        placa,
        min_datetime,
        max_datetime,
        latitude_min,
        latitude_max,
        longitude_min,
        longitude_max,
    )
    bq_client = get_bigquery_client()
    query_job = bq_client.query(query)
    data = query_job.result(page_size=config.GOOGLE_BIGQUERY_PAGE_SIZE)
    hints = sorted(list(set([row["placa"] for row in data])))
    return hints


def get_n_plates_before_and_after(
    placa: str,
    min_datetime: pendulum.DateTime,
    max_datetime: pendulum.DateTime,
    n_minutes: int,
    n_plates: int,
) -> List[NPlatesBeforeAfterOut]:
    """
    Fetch N plates before and after a plate within a time range.

    Args:
        placa (str): The vehicle license plate.
        min_datetime (pendulum.DateTime): The minimum datetime of the range.
        max_datetime (pendulum.DateTime): The maximum datetime of the range.
        n_minutes (int): The number of minutes.
        n_plates (int): The number of plates.

    Returns:
        List[NPlatesBeforeAfterOut]: The plates.
    """
    query, query_params = build_n_plates_query(
        placa=placa,
        min_datetime=min_datetime,
        max_datetime=max_datetime,
        n_minutes=n_minutes,
        n_plates=n_plates,
    )
    bq_client = get_bigquery_client()
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    query_job = bq_client.query(query, job_config=job_config)
    data = query_job.result(page_size=config.GOOGLE_BIGQUERY_PAGE_SIZE)
    n_before_after = []
    for page in data.pages:
        for row in page:
            row: Row
            row_data = dict(row.items())
            n_before_after.append(row_data)
    logger.debug(f"Raw data: {n_before_after}")
    return n_before_after


async def get_positions(
    placa: str,
    min_datetime: pendulum.DateTime,
    max_datetime: pendulum.DateTime,
    min_plate_distance: float = 0,
) -> Dict[str, list]:
    """
    Fetch the positions of a vehicle within a time range.

    Args:
        placa (str): The vehicle license plate.
        min_datetime (pendulum.DateTime): The minimum datetime of the range.
        max_datetime (pendulum.DateTime): The maximum datetime of the range.
        min_plate_distance (float, optional): The minimum distance between plates. Defaults to 0.

    Returns:
        Dict[str, list]: The positions of the vehicle.
    """
    # TODO: Refactor code for using cache again
    # # Get the cached locations
    # cached_locations = await cache.get_positions(placa, min_datetime, max_datetime)
    # logger.debug(f"Retrieved {len(cached_locations)} cached locations for {placa}")

    # # Determine missing range
    # missing_range_start, missing_range_end = await cache.get_missing_range(
    #     placa, min_datetime, max_datetime
    # )
    # logger.debug(f"Missing range for {placa}: {missing_range_start, missing_range_end}")

    # if missing_range_start:
    #     # Query database for missing data and cache it
    #     query = build_positions_query(placa, missing_range_start, missing_range_end)
    #     bq_client = get_bigquery_client()
    #     query_job = bq_client.query(query)
    #     data = query_job.result(page_size=config.GOOGLE_BIGQUERY_PAGE_SIZE)
    #     for page in data.pages:
    #         awaitables = []
    #         for row in page:
    #             row: Row
    #             row_data = dict(row.items())
    #             row_data["datahora"] = pendulum.instance(row_data["datahora"], tz=config.TIMEZONE)
    #             logger.debug(f"Adding position to cache: {row_data}")
    #             awaitables.append(cache.add_position(placa, row_data))
    #         await asyncio.gather(*awaitables)

    # return {"placa": placa, "locations": cached_locations}

    # Query database for missing data and cache it
    query = build_positions_query(
        placa, min_datetime, max_datetime, min_distance=min_plate_distance
    )
    bq_client = get_bigquery_client()
    query_job = bq_client.query(query)
    data = query_job.result(page_size=config.GOOGLE_BIGQUERY_PAGE_SIZE)
    locations = []
    for page in data.pages:
        for row in page:
            row: Row
            row_data = dict(row.items())
            row_data["datahora"] = pendulum.instance(
                row_data["datahora"], tz=config.TIMEZONE
            )
            locations.append(row_data)

    return {"placa": placa, "locations": locations}


@cache_decorator(expire=config.CACHE_REPORTS_METADATA_TTL)
def get_reports_metadata() -> ReportsMetadata:
    """
    Fetches report metadata from BigQuery.
    """
    return get_reports_metadata_no_cache()


def get_reports_metadata_no_cache() -> ReportsMetadata:
    """
    Fetches report metadata from BigQuery.
    """
    query_sources = f"""
        SELECT DISTINCT id_source
        FROM `{config.EMBEDDINGS_SOURCE_TABLE}`
    """
    query_categories = f"""
        SELECT DISTINCT categoria
        FROM `{config.EMBEDDINGS_SOURCE_TABLE}`
    """
    query_types_subtypes = f"""
        SELECT DISTINCT tipo_subtipo.tipo AS tipo, subtipo
        FROM `{config.EMBEDDINGS_SOURCE_TABLE}`,
            UNNEST(tipo_subtipo) AS tipo_subtipo,
            UNNEST(tipo_subtipo.subtipo) AS subtipo
    """
    bq_client = get_bigquery_client()
    query_job_sources = bq_client.query(query_sources)
    query_job_categories = bq_client.query(query_categories)
    query_job_types_subtypes = bq_client.query(query_types_subtypes)
    sources = [row["id_source"] for row in query_job_sources]
    categories = [row["categoria"] for row in query_job_categories]
    types_subtypes = [(row["tipo"], row["subtipo"]) for row in query_job_types_subtypes]
    distinct_types = list(set([t[0] for t in types_subtypes]))
    types_subtypes_dict = {t: [] for t in distinct_types}
    for t, st in types_subtypes:
        types_subtypes_dict[t].append(st)
    return ReportsMetadata(
        distinct_sources=sources,
        distinct_categories=categories,
        distinct_types=distinct_types,
        type_subtypes=types_subtypes_dict,
    )


@cache_decorator(expire=config.CACHE_CAMERAS_COR_TTL)
async def get_cameras_cor() -> list:
    """
    Fetch the cameras list.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                config.TIXXI_CAMERAS_LIST_URL,
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data
    except Exception:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to fetch cameras list")


@cache_decorator(expire=config.CACHE_RADAR_POSITIONS_TTL)
def get_radar_positions() -> List[RadarOut]:
    """
    Fetch the radar positions.

    Returns:
        List[RadarOut]: The radar positions.
    """
    query = """
        WITH radars AS (
            SELECT
                COALESCE(t1.codcet, t2.codcet) AS codcet,
                t2.camera_numero,
                t1.latitude,
                t1.longitude,
                t1.locequip,
                t1.bairro,
                t1.logradouro,
                t1.sentido
            FROM `rj-cetrio.ocr_radar.equipamento` t1
            JOIN `rj-cetrio.ocr_radar.equipamento_codcet_to_camera_numero` t2
                ON t1.codcet = t2.codcet
        ),

        used_radars AS (
        SELECT
            camera_numero,
            camera_latitude,
            camera_longitude,
            empresa,
            MAX(DATETIME(datahora, "America/Sao_Paulo")) AS last_detection_time,
            'yes' AS has_data
        FROM `rj-cetrio.ocr_radar.readings_*`
        GROUP BY camera_numero, camera_latitude, camera_longitude, empresa
        ),

        selected_radar AS (
        SELECT
            t1.codcet,
            COALESCE(t1.camera_numero, t2.camera_numero) AS camera_numero,
            COALESCE(t2.empresa, NULL) AS empresa,
            COALESCE(t1.latitude, t2.camera_latitude) AS latitude,
            COALESCE(t1.longitude, t2.camera_longitude) AS longitude,
            t1.locequip,
            t1.bairro,
            t1.logradouro,
            t1.sentido,
            COALESCE(t2.has_data, 'no') AS has_data,
            COALESCE(t2.last_detection_time, NULL) AS last_detection_time,
            CASE
            WHEN t2.last_detection_time IS NULL THEN NULL
            WHEN TIMESTAMP(t2.last_detection_time) >= TIMESTAMP_SUB(TIMESTAMP(CURRENT_DATETIME("America/Sao_Paulo")), INTERVAL 24 HOUR) THEN 'yes'
            ELSE 'no'
            END AS active_in_last_24_hours
        FROM radars t1
        FULL OUTER JOIN used_radars t2
            ON t1.camera_numero = t2.camera_numero
        )

        SELECT
            *
        FROM selected_radar
        ORDER BY last_detection_time
    """
    bq_client = get_bigquery_client()
    query_job = bq_client.query(query)
    data = query_job.result(page_size=config.GOOGLE_BIGQUERY_PAGE_SIZE)
    positions = []
    for page in data.pages:
        for row in page:
            row: Row
            row_data = dict(row.items())
            positions.append(RadarOut(**row_data))
    return positions


async def get_route_path(
    locations: List[Dict[str, float | pendulum.DateTime]],
) -> Dict[str, Union[int, List]]:
    """
    Get the route path between locations.

    Args:
        locations (List[Dict[str, float | pendulum.DateTime]]): The locations to route.

    Returns:
        Dict[str, Union[int, List]]: The route path.
    """
    # Assert that all locations latitudes and longitudes are floats
    for location in locations:
        if not isinstance(location["latitude"], float):
            latitude = location["latitude"]
            if isinstance(latitude, bytes):
                latitude = latitude.decode("utf-8")
            if isinstance(latitude, str):
                latitude = latitude.replace("'", "")
                latitude = latitude.replace('"', "")
            location["latitude"] = float(latitude)
        if not isinstance(location["longitude"], float):
            longitude = location["longitude"]
            if isinstance(longitude, bytes):
                longitude = longitude.decode("utf-8")
            if isinstance(longitude, str):
                longitude = longitude.replace("'", "")
                longitude = longitude.replace('"', "")
            location["longitude"] = float(longitude)

    # https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes
    payload = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": locations[0]["latitude"],
                    "longitude": locations[0]["longitude"],
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": locations[-1]["latitude"],
                    "longitude": locations[-1]["longitude"],
                }
            }
        },
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        # "departureTime": "2023-10-15T15:01:23.045123456Z",
        "computeAlternativeRoutes": False,
        # "routeModifiers": {
        #   "avoidTolls": false,
        #   "avoidHighways": false,
        #   "avoidFerries": false
        # },
        "polylineEncoding": "GEO_JSON_LINESTRING",
        "languageCode": "pt-BR",
        "units": "METRIC",
    }
    if len(locations) > 2:
        payload["intermediates"] = [
            {
                "location": {
                    "latLng": {
                        "latitude": location["latitude"],
                        "longitude": location["longitude"],
                    }
                }
            }
            for location in locations[1:-1]
        ]
    # https://developers.google.com/maps/documentation/routes/compute_route_directions#go
    async with AsyncClient(timeout=None) as client:
        r = await client.post(
            "https://routes.googleapis.com/directions/v2:computeRoutes",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": config.GOOGLE_MAPS_API_KEY,
                "X-Goog-FieldMask": "routes.legs",
            },
        )
        return r.json()


async def get_waze_alerts_for_coords(coords: dict) -> list:
    url = "https://www.waze.com/row-rtserver/web/TGeoRSS?bottom={bottom}&left={left}&ma=200&mj=200&mu=20&right={right}&top={top}&types=alerts"  # noqa
    url = url.format(**coords)
    async with AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json().get("alerts", [])


@cache_decorator(expire=config.CACHE_WAZE_ALERTS_TTL)
async def get_waze_alerts(filter_type: str = None) -> list:
    coords = [
        {
            "left": -43.79653853090349,
            "bottom": -23.08289269734031,
            "right": -43.62216601277018,
            "top": -22.91445704293636,
        },
        {
            "left": -43.79653853090349,
            "bottom": -22.91445704293636,
            "right": -43.62216601277018,
            "top": -22.74602138853241,
        },
        {
            "left": -43.62216601277018,
            "bottom": -23.08289269734031,
            "right": -43.44779349463688,
            "top": -22.91445704293636,
        },
        {
            "left": -43.62216601277018,
            "bottom": -22.91445704293636,
            "right": -43.44779349463688,
            "top": -22.74602138853241,
        },
        {
            "left": -43.44779349463688,
            "bottom": -23.08289269734031,
            "right": -43.36060723557023,
            "top": -22.91445704293636,
        },
        {
            "left": -43.36060723557023,
            "bottom": -23.08289269734031,
            "right": -43.27342097650357,
            "top": -22.91445704293636,
        },
        {
            "left": -43.44779349463688,
            "bottom": -22.91445704293636,
            "right": -43.36060723557023,
            "top": -22.83023921573439,
        },
        {
            "left": -43.44779349463688,
            "bottom": -22.83023921573439,
            "right": -43.36060723557023,
            "top": -22.74602138853241,
        },
        {
            "left": -43.36060723557023,
            "bottom": -22.91445704293636,
            "right": -43.27342097650357,
            "top": -22.83023921573439,
        },
        {
            "left": -43.36060723557023,
            "bottom": -22.83023921573439,
            "right": -43.3170141060369,
            "top": -22.74602138853241,
        },
        {
            "left": -43.3170141060369,
            "bottom": -22.83023921573439,
            "right": -43.27342097650357,
            "top": -22.74602138853241,
        },
        {
            "left": -43.27342097650357,
            "bottom": -23.08289269734031,
            "right": -43.18623471743692,
            "top": -22.99867487013834,
        },
        {
            "left": -43.27342097650357,
            "bottom": -22.99867487013834,
            "right": -43.22982784697025,
            "top": -22.91445704293636,
        },
        {
            "left": -43.22982784697025,
            "bottom": -22.99867487013834,
            "right": -43.18623471743692,
            "top": -22.91445704293636,
        },
        {
            "left": -43.18623471743692,
            "bottom": -23.08289269734031,
            "right": -43.09904845837026,
            "top": -22.91445704293636,
        },
        {
            "left": -43.27342097650357,
            "bottom": -22.91445704293636,
            "right": -43.22982784697025,
            "top": -22.83023921573439,
        },
        {
            "left": -43.22982784697025,
            "bottom": -22.91445704293636,
            "right": -43.18623471743692,
            "top": -22.83023921573439,
        },
        {
            "left": -43.27342097650357,
            "bottom": -22.83023921573439,
            "right": -43.18623471743692,
            "top": -22.74602138853241,
        },
        {
            "left": -43.18623471743692,
            "bottom": -22.91445704293636,
            "right": -43.09904845837026,
            "top": -22.74602138853241,
        },
    ]
    awaitables = []
    for coord in coords:
        awaitables.append(get_waze_alerts_for_coords(coord))
    responses = await asyncio.gather(*awaitables)
    alerts = [alert for response in responses for alert in response]
    if filter_type:
        filter_type = filter_type.upper()
        alerts = [alert for alert in alerts if alert["type"].upper() == filter_type]
    return alerts


def normalize_waze_alerts(alerts: List[Dict[str, Any]]) -> List[WazeAlertOut]:
    return [
        WazeAlertOut(
            timestamp=DateTime.fromtimestamp(
                alert["pubMillis"] / 1000, tz=pytz.timezone(config.TIMEZONE)
            ),
            street=alert["street"] if "street" in alert else None,
            type=alert["type"],
            subtype=alert["subtype"],
            reliability=alert["reliability"],
            confidence=alert["confidence"],
            number_thumbs_up=alert["nThumbsUp"] if "nThumbsUp" in alert else None,
            latitude=alert["location"]["y"],
            longitude=alert["location"]["x"],
        )
        for alert in alerts
    ]


def register_tortoise(
    app: FastAPI,
    config: Optional[dict] = None,
    config_file: Optional[str] = None,
    db_url: Optional[str] = None,
    modules: Optional[Dict[str, Iterable[Union[str, ModuleType]]]] = None,
    generate_schemas: bool = False,
    add_exception_handlers: bool = False,
) -> AbstractAsyncContextManager:
    """Custom implementation of `register_tortoise` for lifespan support"""

    async def init_orm() -> None:  # pylint: disable=W0612
        await Tortoise.init(
            config=config, config_file=config_file, db_url=db_url, modules=modules
        )
        logger.info(
            f"Tortoise-ORM started, {connections._get_storage()}, {Tortoise.apps}"
        )
        if generate_schemas:
            logger.info("Tortoise-ORM generating schema")
            await Tortoise.generate_schemas()

    async def close_orm() -> None:  # pylint: disable=W0612
        await connections.close_all()
        logger.info("Tortoise-ORM shutdown")

    class Manager(AbstractAsyncContextManager):
        async def __aenter__(self) -> "Manager":
            await init_orm()
            return self

        async def __aexit__(self, *args, **kwargs) -> None:
            await close_orm()

    if add_exception_handlers:

        @app.exception_handler(DoesNotExist)
        async def doesnotexist_exception_handler(request: Request, exc: DoesNotExist):
            return JSONResponse(status_code=404, content={"detail": str(exc)})

        @app.exception_handler(IntegrityError)
        async def integrityerror_exception_handler(
            request: Request, exc: IntegrityError
        ):
            return JSONResponse(
                status_code=422,
                content={
                    "detail": [{"loc": [], "msg": str(exc), "type": "IntegrityError"}]
                },
            )

    return Manager()


async def search_weaviate(
    filters: ReportFilters,
    order_by: ReportsOrderBy,
    search_mode: ReportsSearchMode,
) -> Tuple[List[dict], int]:
    query = await build_graphql_query(
        filters=filters, order_by=order_by, search_mode=search_mode
    )
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{config.WEAVIATE_BASE_URL}/v1/graphql",
            json={"query": query},
        ) as response:
            response.raise_for_status()
            data = await response.json()
            reports = []
            count = data["data"]["Aggregate"][config.WEAVIATE_SCHEMA_CLASS][0]["meta"][
                "count"
            ]
            for item in data["data"]["Get"][config.WEAVIATE_SCHEMA_CLASS]:
                reports.append(
                    dict(
                        **item,
                        additional_info=item["_additional"]
                        if "_additional" in item
                        else None,
                    )
                )
            return reports, count


def translate_method_to_action(method: str) -> str:
    mapping = {
        "GET": "read",
        "POST": "create",
        "PUT": "update",
        "DELETE": "delete",
    }
    return mapping.get(method.upper(), "read")


def validate_cpf(cpf: str) -> bool:
    def validate_digits(numbers):
        # Validação do primeiro dígito verificador:
        sum_of_products = sum(a * b for a, b in zip(numbers[:9], range(10, 1, -1)))
        expected_digit = (sum_of_products * 10) % 11 % 10
        if numbers[9] != expected_digit:
            return False

        # Validação do segundo dígito verificador:
        sum_of_products = sum(a * b for a, b in zip(numbers[:10], range(11, 1, -1)))
        expected_digit = (sum_of_products * 10) % 11 % 10
        if numbers[10] != expected_digit:
            return False

        return True

    numbers = [int(digit) for digit in cpf if digit.isdigit()]

    if len(numbers) != 11 or len(set(numbers)) == 1:
        return False

    if not validate_digits(numbers):
        return False

    return True


def validate_cnpj(cnpj: str) -> bool:
    # Adapted from: https://wiki.python.org.br/VerificadorDeCpfCnpjSimples
    cnpj = "".join(re.findall("\d", str(cnpj)))

    if (not cnpj) or (len(cnpj) < 14):
        return False

    # Pega apenas os 12 primeiros dígitos do CNPJ e gera os 2 dígitos que faltam
    inteiros = [int(c) for c in cnpj]
    novo = inteiros[:12]

    prod = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    while len(novo) < 14:
        r = sum([x * y for (x, y) in zip(novo, prod)]) % 11
        if r > 1:
            f = 11 - r
        else:
            f = 0
        novo.append(f)
        prod.insert(0, 6)

    # Se o número gerado coincidir com o número original, é válido
    if novo == inteiros:
        return cnpj
    return False


def validate_plate(plate: str) -> bool:
    # Ensure the plate is upper case
    plate = plate.upper()

    # Ensure the plate has the correct format
    pattern = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")
    if not pattern.match(plate):
        return False

    return True
