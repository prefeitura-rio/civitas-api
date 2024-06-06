# -*- coding: utf-8 -*-
import asyncio
import base64
from contextlib import AbstractAsyncContextManager
from types import ModuleType
from typing import Dict, Iterable, List, Optional, Union

import googlemaps
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
    SELECT
        DATETIME(datahora, "America/Sao_Paulo") AS datahora,
        camera_numero,
        camera_longitude AS longitude,
        camera_latitude AS latitude
    FROM `rj-cetrio.ocr_radar.readings_2024_05`
    WHERE
        placa = "{{placa}}"
        AND TIMESTAMP_TRUNC(DATETIME(datahora, "America/Sao_Paulo"), HOUR) >= TIMESTAMP_TRUNC(DATETIME("{{min_datetime}}"), HOUR)
        AND TIMESTAMP_TRUNC(DATETIME(datahora, "America/Sao_Paulo"), HOUR) <= TIMESTAMP_TRUNC(DATETIME("{{max_datetime}}"), HOUR)
    ORDER BY datahora ASC, placa ASC
    """.replace(
            "{{placa}}", placa
        )
        .replace("{{min_datetime}}", min_datetime.to_datetime_string())
        .replace("{{max_datetime}}", max_datetime.to_datetime_string())
    )

    return query


def chunk_locations(locations, N):
    if not locations or N <= 0:
        return []

    # Initialize the list to hold chunks
    chunks = []

    # Start with the first chunk
    for i in range(0, len(locations), N):
        # If it's the first chunk, just add it
        if i == 0:
            chunks.append(locations[i : i + N])
        else:
            # For subsequent chunks, ensure the first element is the last of the previous chunk
            previous_chunk = chunks[-1]
            current_chunk = [previous_chunk[-1]] + locations[i : i + N - 1]
            chunks.append(current_chunk)

    return chunks


def convert_to_geojson_linestring(coordinates, duration, static_duration, index_chunk, index_trip):
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [(point["lng"], point["lat"]) for point in coordinates],
        },
        "properties": {
            "index_trip": index_trip,
            "index_chunk": index_chunk,
            "duration": duration,
            "staticDuration": static_duration,
        },
    }


def convert_to_geojson_point(locations, index_chunk, index_trip):
    features = []
    for i, location in enumerate(locations):
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [location["longitude"], location["latitude"]],
                },
                "properties": {
                    "index_trip": index_trip,
                    "index_chunk": index_chunk,
                    "index": i,
                    "datahora": location["datahora"],
                    "camera_numero": location["camera_numero"],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


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


def get_trips_chunks(locations, max_time_interval):
    for point in locations:
        point["datetime"] = point["datahora"]

    chunks = []
    current_chunk = [locations[0]]

    for i in range(1, len(locations)):
        point_anterior = locations[i - 1]
        point_atual = locations[i]

        diferenca_tempo = (point_atual["datetime"] - point_anterior["datetime"]).total_seconds()

        if diferenca_tempo > max_time_interval:
            chunks.append(current_chunk)
            current_chunk = [point_atual]
        else:
            current_chunk.append(point_atual)

    chunks.append(current_chunk)

    for chunk in chunks:
        for point in chunk:
            point.pop("datetime")

    return chunks


@cache_decorator(expire=config.CACHE_CAR_PATH_TTL)
async def get_path(placa: str, min_datetime: pendulum.DateTime, max_datetime: pendulum.DateTime):
    locations_interval = (await get_positions(placa, min_datetime, max_datetime))["locations"]
    locations_trips = get_trips_chunks(locations=locations_interval, max_time_interval=60 * 60)

    locations_geojson_trips = []
    polyline_geojson_trips = []
    for j, locations in enumerate(locations_trips):
        locations_chunks = chunk_locations(
            locations=locations, N=config.GOOGLE_MAPS_API_MAX_POINTS_PER_REQUEST
        )

        coordinates = []
        total_duration = 0
        total_duration_static = 0
        final_paths_chunks = []
        polyline_geojson_chunks = []
        locations_geojson_chunks = []

        for i, location_chunk in enumerate(locations_chunks):
            route = await get_route_path(locations=location_chunk, index_chunk=i, index_trip=j)
            coordinates += route["coordinates"]
            total_duration += route["duration"]
            total_duration_static += route["staticDuration"]
            polyline_geojson_chunks.append(route["polylineGeojson"])
            locations_geojson_chunks.append(route["locationsGeojson"])
            final_paths_chunks.append(route)

        polyline_geojson_trips.append(polyline_geojson_chunks)
        locations_geojson_trips.append(locations_geojson_chunks)

    path = {
        "polylineChunksGeojson": polyline_geojson_trips,
        "locationsChunksGeojson": locations_geojson_trips,
    }

    return path


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
    locations: List[Dict[str, float | pendulum.DateTime]], index_chunk: int, index_trip: int
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
        # "polylineEncoding":"GEO_JSON_LINESTRING",
        "languageCode": "en-US",
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
                "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters,routes.polyline.encodedPolyline",
            },
        )
        route = r.json()["routes"][0]

    route["duration"] = int(route["duration"].replace("s", ""))
    route["staticDuration"] = int(route["staticDuration"].replace("s", ""))

    decoded_path = googlemaps.convert.decode_polyline(route["polyline"]["encodedPolyline"])
    route["coordinates"] = decoded_path

    route["polylineGeojson"] = convert_to_geojson_linestring(
        coordinates=decoded_path,
        duration=route["duration"],
        static_duration=route["staticDuration"],
        index_chunk=index_chunk,
        index_trip=index_trip,
    )

    route["locationsGeojson"] = convert_to_geojson_point(
        locations=locations, index_chunk=index_chunk, index_trip=index_trip
    )

    return route


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
