# -*- coding: utf-8 -*-
import asyncio
import base64
from contextlib import AbstractAsyncContextManager
from types import ModuleType
from typing import Dict, Iterable, List, Optional, Union

import orjson as json
import pendulum
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi_cache.decorator import cache as cache_decorator
from google.cloud import bigquery
from google.cloud.bigquery.table import Row
from google.oauth2 import service_account
from httpx import AsyncClient
from loguru import logger
from tortoise import Tortoise, connections
from tortoise.exceptions import DoesNotExist, IntegrityError

from app import cache, config


def build_positions_query(
    placa: str, min_datetime: pendulum.DateTime, max_datetime: pendulum.DateTime
) -> str:
    """
    Build a SQL query to fetch the positions of a vehicle within a time range.

    Args:
        placa (str): The vehicle license plate.
        min_datetime (pendulum.DateTime): The minimum datetime of the range.
        max_datetime (pendulum.DateTime): The maximum datetime of the range.

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
                    camera_longitude
            FROM `rj-cetrio.ocr_radar.readings_*`
            WHERE
                placa IN ("{{placa}}")
                AND (camera_latitude != 0 AND camera_longitude != 0)
                AND DATETIME_TRUNC(DATETIME(datahora, "America/Sao_Paulo"), HOUR) >= DATETIME_TRUNC(DATETIME("{{min_datetime}}"), HOUR)
                AND DATETIME_TRUNC(DATETIME(datahora, "America/Sao_Paulo"), HOUR) <= DATETIME_TRUNC(DATETIME("{{max_datetime}}"), HOUR)
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
            l.localidade
        FROM ordered_positions p
        JOIN loc l ON p.camera_numero = l.camera_numero
        ORDER BY p.datahora ASC
        """.replace(
            "{{placa}}", placa
        )
        .replace("{{min_datetime}}", min_datetime.to_datetime_string())
        .replace("{{max_datetime}}", max_datetime.to_datetime_string())
    )

    return query


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


def chunk_locations(locations, N):
    chunks = []
    i = 0
    while i < len(locations):
        if i + N <= len(locations):
            chunk = locations[i : i + N]
            chunks.append(chunk)
            i += N - 1
        else:
            if len(locations[i:]) > 1:
                chunk = locations[i:]
                chunks.append(chunk)
            break
    return chunks


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

        diferenca_tempo = (point_atual["datetime"] - point_anterior["datetime"]).total_seconds()
        point_anterior["seconds_to_next_point"] = diferenca_tempo
        if diferenca_tempo > max_time_interval:
            point_anterior["seconds_to_next_point"] = None
            chunks.append(current_chunk)
            current_chunk = [point_atual]
        else:
            current_chunk.append(point_atual)

    current_chunk[-1][
        "seconds_to_next_point"
    ] = None  # Ensure the last point in the final chunk has None
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
) -> List[Dict[str, Union[str, List]]]:
    locations_interval = (await get_positions(placa, min_datetime, max_datetime))["locations"]
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


async def get_positions(
    placa: str, min_datetime: pendulum.DateTime, max_datetime: pendulum.DateTime
) -> Dict[str, list]:
    """
    Fetch the positions of a vehicle within a time range.

    Args:
        placa (str): The vehicle license plate.
        min_datetime (pendulum.DateTime): The minimum datetime of the range.
        max_datetime (pendulum.DateTime): The maximum datetime of the range.

    Returns:
        Dict[str, list]: The positions of the vehicle.
    """
    # Get the cached locations
    cached_locations = await cache.get_positions(placa, min_datetime, max_datetime)
    logger.debug(f"Retrieved {len(cached_locations)} cached locations for {placa}")

    # Determine missing range
    missing_range_start, missing_range_end = await cache.get_missing_range(
        placa, min_datetime, max_datetime
    )
    logger.debug(f"Missing range for {placa}: {missing_range_start, missing_range_end}")

    if missing_range_start:
        # Query database for missing data and cache it
        query = build_positions_query(placa, missing_range_start, missing_range_end)
        bq_client = get_bigquery_client()
        query_job = bq_client.query(query)
        data = query_job.result(page_size=config.GOOGLE_BIGQUERY_PAGE_SIZE)
        for page in data.pages:
            awaitables = []
            for row in page:
                row: Row
                row_data = dict(row.items())
                row_data["datahora"] = pendulum.instance(row_data["datahora"], tz=config.TIMEZONE)
                logger.debug(f"Adding position to cache: {row_data}")
                awaitables.append(cache.add_position(placa, row_data))
            await asyncio.gather(*awaitables)

        # Retrieve all locations again, now with the missing data filled in
        cached_locations = await cache.get_positions(placa, min_datetime, max_datetime)
        logger.debug(
            f"Retrieved {len(cached_locations)} cached locations (after BQ fetch) for {placa}"
        )

    return {"placa": placa, "locations": cached_locations}


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
        await Tortoise.init(config=config, config_file=config_file, db_url=db_url, modules=modules)
        logger.info(f"Tortoise-ORM started, {connections._get_storage()}, {Tortoise.apps}")
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
        async def integrityerror_exception_handler(request: Request, exc: IntegrityError):
            return JSONResponse(
                status_code=422,
                content={"detail": [{"loc": [], "msg": str(exc), "type": "IntegrityError"}]},
            )

    return Manager()
