# -*- coding: utf-8 -*-
import asyncio
import base64
from contextlib import AbstractAsyncContextManager
from types import ModuleType
from typing import Any, Dict, Iterable, List, Optional, Union
from uuid import UUID

import orjson as json
import pendulum
import pytz
from fastapi import FastAPI, Request
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
from app.models import GroupUser, Resource, User
from app.pydantic_models import CarPassageOut, RadarOut, WazeAlertOut


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
    plate_hint = plate_hint.upper().replace("*", "%") if plate_hint else None

    query = """
        SELECT
            placa,
            DATETIME(datahora, "America/Sao_Paulo") AS datahora,
        FROM `rj-cetrio.ocr_radar.readings_*`
        WHERE
            DATETIME(datahora, "America/Sao_Paulo") >= DATETIME("{{min_datetime}}")
            AND DATETIME(datahora, "America/Sao_Paulo") <= DATETIME("{{max_datetime}}")
    """.replace(
        "{{min_datetime}}", min_datetime.to_datetime_string()
    ).replace(
        "{{max_datetime}}", max_datetime.to_datetime_string()
    )

    if codcet:
        query += f"AND (camera_numero = '{codcet}' OR camera_numero = '{camera_numero}')"
    else:
        query += f"AND camera_numero = '{camera_numero}'"

    if plate_hint:
        query += f"AND placa LIKE '{plate_hint}'"

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

    placa = placa.upper().replace("*", "%")

    query = """
        SELECT
            placa
        FROM `rj-cetrio.ocr_radar.readings_*`
        WHERE
            placa LIKE '{{placa}}'
    """.replace(
        "{{placa}}", placa
    )

    if latitude_min and latitude_max:
        query += """
            AND (camera_latitude BETWEEN {{latitude_min}} AND {{latitude_max}})
        """.replace(
            "{{latitude_min}}", str(latitude_min)
        ).replace(
            "{{latitude_max}}", str(latitude_max)
        )

    if longitude_min and longitude_max:
        query += """
            AND (camera_longitude BETWEEN {{longitude_min}} AND {{longitude_max}})
        """.replace(
            "{{longitude_min}}", str(longitude_min)
        ).replace(
            "{{longitude_max}}", str(longitude_max)
        )

    query += """
            AND DATETIME(datahora, "America/Sao_Paulo") >= DATETIME("{{min_datetime}}")
            AND DATETIME(datahora, "America/Sao_Paulo") <= DATETIME("{{max_datetime}}")
        GROUP BY placa
    """.replace(
        "{{min_datetime}}", min_datetime.to_datetime_string()
    ).replace(
        "{{max_datetime}}", max_datetime.to_datetime_string()
    )

    return query


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
                    camera_longitude
            FROM `rj-cetrio.ocr_radar.readings_*`
            WHERE
                `rj-cetrio`.ocr_radar.plateDistance(placa, "{{placa}}") <= {{min_distance}}
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
            l.localidade
        FROM ordered_positions p
        JOIN loc l ON p.camera_numero = l.camera_numero
        ORDER BY p.datahora ASC
        """.replace(
            "{{placa}}", placa
        )
        .replace("{{min_datetime}}", min_datetime.to_datetime_string())
        .replace("{{max_datetime}}", max_datetime.to_datetime_string())
        .replace("{{min_distance}}", str(min_distance))
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
            car_passages.append(CarPassageOut(plate=placa, timestamp=datahora))
    # Sort car passages by timestamp ascending
    car_passages = sorted(car_passages, key=lambda x: x.timestamp)
    return car_passages


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
        placa, min_datetime, max_datetime, latitude_min, latitude_max, longitude_min, longitude_max
    )
    bq_client = get_bigquery_client()
    query_job = bq_client.query(query)
    data = query_job.result(page_size=config.GOOGLE_BIGQUERY_PAGE_SIZE)
    hints = sorted(list(set([row["placa"] for row in data])))
    return hints


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
            row_data["datahora"] = pendulum.instance(row_data["datahora"], tz=config.TIMEZONE)
            locations.append(row_data)

    return {"placa": placa, "locations": locations}


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
        WHERE
            codcet IS NOT NULL
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


def translate_method_to_action(method: str) -> str:
    mapping = {
        "GET": "read",
        "POST": "create",
        "PUT": "update",
        "DELETE": "delete",
    }
    return mapping.get(method.upper(), "read")


async def update_resources_list(app: FastAPI):
    """
    Update the resources list with the current routes.

    Args:
        app (FastAPI): The FastAPI app
    """
    # Get list of current resources
    current_resources = sorted(list(set([route.path[1:] for route in app.routes])))
    current_resources = [
        resource for resource in current_resources if resource not in config.RBAC_EXCLUDED_PATHS
    ]

    # Create list of awaitables for database resources
    awaitables = []

    # Eliminate resources from database that are not in the current resources list
    for resource in await Resource.all():
        if resource.name not in current_resources:
            awaitables.append(resource.delete())

    # Add resources to database that are not in the database
    for resource in current_resources:
        if await Resource.filter(name=resource).exists():
            continue
        awaitables.append(Resource.create(name=resource))

    # Execute all awaitables
    await asyncio.gather(*awaitables)


@cache_decorator(expire=config.RBAC_PERMISSIONS_CACHE_TTL)
async def user_is_group_admin(group_id: UUID, user: User) -> bool:
    if user.is_admin:
        return True
    elif GroupUser.filter(group__id=group_id, user=user, is_group_admin=True).exists():
        return True
    return False


@cache_decorator(expire=config.RBAC_PERMISSIONS_CACHE_TTL)
async def user_is_group_member(group_id: UUID, user: User) -> bool:
    if user.is_admin:
        return True
    elif GroupUser.filter(group__id=group_id, user=user).exists():
        return True
    return False


@cache_decorator(expire=config.RBAC_PERMISSIONS_CACHE_TTL)
async def user_has_permission(user: User, action: str, resource: str) -> bool:
    return True  # TODO: implement
    # user_permissions = await Permission.filter(
    #     role__group=user.group, action=action, resource=resource
    # ).all()

    # parent_group = await user.group.parent_group
    # if parent_group:
    #     parent_permissions = await Permission.filter(
    #         role__group=parent_group, action=action, resource=resource
    #     ).all()
    #     return bool(user_permissions) and bool(parent_permissions)
    # return bool(user_permissions)
