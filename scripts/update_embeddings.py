# -*- coding: utf-8 -*-
import asyncio
import gc
import traceback
import uuid
from datetime import datetime
from math import isnan
from typing import Any, Awaitable, Dict, List

import orjson as json
import pytz
import requests
import unidecode
from google.cloud.bigquery.table import Row
from loguru import logger
from pendulum import DateTime
from redis import Redis
from redis.lock import Lock

from app import config
from app.pydantic_models import ReportOut, ReportsMetadata
from app.utils import (
    generate_embeddings_batch,
    get_bigquery_client,
    get_reports_metadata_no_cache,
)

EMBEDDING_COLUMNS = [
    "orgaos",
    "categoria",
    "tipo_subtipo",
    "descricao",
    "logradouro",
    "numero_logradouro",
]
EMBEDDINGS_LAST_UPDATE_KEY = "embeddings_last_update"
UPDATE_EMBEDDINGS_LOCK_KEY = "update_embeddings_lock"


def generate_text_for_embedding(item: Dict[str, Any]) -> str:
    """
    Generate a text to be used for generating an embedding.

    Args:
        item (Dict[str, Any]): A dictionary with the item's data.

    Returns:
        str: A text to be used for generating an embedding.
    """
    text = ""
    for column in EMBEDDING_COLUMNS:
        value = item.get(column)
        if value:
            text += f"{value} "
    return text.strip()


def generate_uuid5(identifier: Any, namespace: Any = "") -> str:
    """
    Generate an UUIDv5, may be used to consistently generate the same UUID for a specific
    identifier and namespace.

    Parameters
    ----------
    identifier : Any
        The identifier/object that should be used as basis for the UUID.
    namespace : Any, optional
        Allows to namespace the identifier, by default ""

    Returns
    -------
    str
        The UUID as a string.
    """
    # This was simply copied and adapted from Weaviate's Python client code. We weren't able to add
    # it as a dependency due to subdependencies conflicts.
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(namespace) + str(identifier)))


def get_sources() -> Dict[str, str]:
    """
    Get the report sources.

    Returns:
        List[str]: A list of report sources.
    """
    metadata: ReportsMetadata = get_reports_metadata_no_cache()
    original_sources = metadata.distinct_sources
    sources_slug = [to_snake_case(source) for source in metadata.distinct_sources]
    return dict(zip(original_sources, sources_slug))


def get_sources_last_update_key(source_slug: str) -> str:
    """
    Get the Redis key for the last update timestamp for a report source.

    Args:
        source_slug (str): The report source slug.

    Returns:
        str: The Redis key for the last update timestamp for the report source.
    """
    return f"{EMBEDDINGS_LAST_UPDATE_KEY}__{source_slug}"


def get_sources_last_update(
    redis_client: Redis = None, sources: Dict[str, str] = None
) -> Dict[str, DateTime]:
    """
    Get the last update timestamp for each report source from Redis.

    Args:
        redis_client (Redis, optional): A Redis client. Defaults to None.
        sources (Dict[str, str], optional): A dictionary with the report sources. Defaults to None.

    Returns:
        Dict[str, DateTime]: A dictionary with the last update timestamp for each report source.
    """
    redis = redis_client or get_redis_client()
    if not sources:
        sources = get_sources()
    sources_last_update = {}
    for source, slug in sources.items():
        val: bytes = redis.get(get_sources_last_update_key(slug))
        last_update = float(val.decode()) if val else None
        sources_last_update[source] = (
            DateTime.fromtimestamp(last_update, tz=pytz.timezone(config.TIMEZONE))
            if last_update
            else None
        )
    return sources_last_update


def get_lock(redis_client: Redis = None) -> Lock:
    """
    Get a lock for updating embeddings.

    Args:
        redis_client (Redis, optional): A Redis client. Defaults to None.

    Returns:
        Lock: A lock for updating embeddings.
    """
    redis = redis_client or get_redis_client()
    return Lock(
        redis,
        UPDATE_EMBEDDINGS_LOCK_KEY,
        timeout=config.UPDATE_EMBEDDINGS_LOCK_TIMEOUT,
    )


def get_redis_client() -> Redis:
    """
    Get a Redis client.

    Returns:
        Redis: A Redis client.
    """
    return Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
        password=config.REDIS_PASSWORD,
    )


def get_reports_since_last_update(
    source: str, last_update: DateTime = None
) -> List[ReportOut]:
    """
    Get reports since the last update timestamp.

    Args:
        source (str): The report source.
        last_update (DateTime, optional): The last update timestamp. Defaults to None.

    Returns:
        List[ReportOut]: A list of reports.
    """
    client = get_bigquery_client()
    query = f"""
        SELECT *
        FROM {config.EMBEDDINGS_SOURCE_TABLE}
        WHERE {config.EMBEDDINGS_SOURCE_TABLE_SOURCE_COLUMN} = '{source}'
    """
    if last_update:
        query += f"""
        AND {config.EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN} >
            TIMESTAMP('{last_update}')
        """
    query += f"""
        ORDER BY {config.EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN} ASC
    """
    query_job = client.query(query)
    data = query_job.result(page_size=config.GOOGLE_BIGQUERY_PAGE_SIZE)
    reports = []
    for page in data.pages:
        for row in page:
            row: Row
            row_data = dict(row)
            reports.append(ReportOut(**row_data))
    return reports


def run_sync(func: Awaitable[Any], *args: Any, **kwargs: Any) -> Any:
    """
    Run an asynchronous function synchronously.

    Args:
        func (Awaitable[Any]): An asynchronous function.
        *args (Any): Positional arguments to pass to the function.
        **kwargs (Any): Keyword arguments to pass to the function.

    Returns:
        Any: The return value of the function.
    """
    return asyncio.run(func(*args, **kwargs))


def send_discord_message(message: str):
    """
    Send a message to a Discord channel.

    Args:
        message (str): The message to send.
    """
    webhook_url = config.UPDATE_EMBEDDINGS_DEBUG_DISCORD_WEBHOOK
    if webhook_url:
        response = requests.post(webhook_url, json={"content": message})
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            logger.error(f"Failed to send Discord message: {exc}")
            logger.error(response.text)
            raise


def set_last_update(
    last_update: DateTime, source_slug: str, redis_client: Redis = None
):
    """
    Set the last update timestamp in Redis.

    Args:
        last_update (DateTime): The last update timestamp.
        source_slug (str): The report source slug.
        redis_client (Redis, optional): A Redis client. Defaults to None.
    """
    redis = redis_client or get_redis_client()
    redis.set(get_sources_last_update_key(source_slug), last_update.timestamp())


def to_snake_case(string: str) -> str:
    """
    Convert a string to snake case. Also remove double spaces, accents, and special characters.

    Args:
        string (str): A string.

    Returns:
        str: The string in snake case.
    """
    string = string.lower().replace(" ", "_")
    string = unidecode.unidecode(string)
    return "".join(char for char in string if char.isalnum() or char == "_")


def upload_batch_to_weaviate(items: List[Dict[str, Any]]):
    """
    Upload a batch of items to Weaviate.

    Args:
        items (List[Dict[str, Any]]): A list of items to upload.
    """
    data_objects = []
    for item in items:
        # Create a copy of the keys to avoid modifying the dictionary during iteration
        keys = list(item.keys())
        for key in keys:
            value = item[key]
            if isinstance(value, datetime):
                timestamp: datetime = item[key]
                timestamp_formatted = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
                timestamp_seconds = int(timestamp.timestamp())
                item[key] = timestamp_formatted
                item[f"{key}_seconds"] = timestamp_seconds
        
        item_properties = {k: v for k, v in item.items() if k != "embedding"}
        latitude = item_properties.get("latitude")
        if latitude and isnan(latitude):
            item_properties["latitude"] = None
        longitude = item_properties.get("longitude")
        if longitude and isnan(longitude):
            item_properties["longitude"] = None
        data_object = {
            "class": config.WEAVIATE_SCHEMA_CLASS,
            "id": generate_uuid5(item[config.EMBEDDINGS_SOURCE_TABLE_ID_COLUMN]),
            "properties": item_properties,
            "vector": item["embedding"],
        }
        data_objects.append(data_object)
    try:
        response = requests.post(
            f"{config.WEAVIATE_BASE_URL}/v1/batch/objects",
            json={"fields": ["ALL"], "objects": data_objects},
            timeout=300
        )
        response.raise_for_status()
    except Exception as exc:
        logger.error(f"Failed to upload embeddings to Weaviate: {exc}")
        raise exc
    data = response.json()
    for result in data:
        if "errors" in result["result"]:
            raise Exception(result["result"]["errors"])
        
    # free memory
    del data_objects
    del data
    gc.collect()


if __name__ == "__main__":
    logger.info("Starting a new round of updating embeddings.")
    lock = get_lock()
    try:
        # Acquire lock
        logger.info("Attempting to get lock...")
        if not lock.acquire(blocking=False):
            logger.info("Lock is already acquired. Exiting.")
            exit()
        logger.info("Lock acquired.")
        # List sources
        logger.info("Listing reports sources...")
        sources = get_sources()
        logger.info(
            f"Found {len(sources)} sources: {[source for source in sources.keys()]}"
        )
        logger.info("Getting last update timestamps for sources...")
        # Get last update for each source
        sources_last_update = get_sources_last_update(sources=sources)
        for source, last_update in sources_last_update.items():
            if last_update:
                logger.info(f"  * {source}: {last_update}")
            else:
                logger.info(f"  * {source}: No last update timestamp found.")
        # Iterate over sources and update embeddings
        for source, source_slug in sources.items():
            # Get reports since last update
            logger.info(f"Getting reports since last update for {source}...")
            last_update = sources_last_update[source]
            reports = get_reports_since_last_update(
                source=source, last_update=last_update
            )
            # # TODO: this is a temporary fix to avoid empty latitudes and longitudes
            # reports = [report for report in reports if report.latitude and report.longitude]
            if len(reports) > 0:
                # Create batches for processing
                logger.info(
                    f"  * Found {len(reports)} reports for source '{source}' since {last_update}"
                )
                logger.info(f"Getting embeddings for reports of source '{source}'...")
                items = [item.dict() for item in reports]
                texts = [generate_text_for_embedding(item) for item in items]
                num_batches = len(items) // config.UPDATE_EMBEDDINGS_BATCH_SIZE
                if len(items) % config.UPDATE_EMBEDDINGS_BATCH_SIZE > 0:
                    num_batches += 1

                # Process batches
                for i in range(0, len(items), config.UPDATE_EMBEDDINGS_BATCH_SIZE):
                    batch_number = i // config.UPDATE_EMBEDDINGS_BATCH_SIZE + 1
                    items_batch = items[i : i + config.UPDATE_EMBEDDINGS_BATCH_SIZE]
                    texts_batch = texts[i : i + config.UPDATE_EMBEDDINGS_BATCH_SIZE]

                    # Generate embeddings for batch
                    embeddings_batch = run_sync(generate_embeddings_batch, texts_batch)
                    items_with_embeddings_batch = [
                        {
                            **item,
                            "embedding": embedding,
                            "report_data_raw": json.dumps(item).decode().lower(),
                        }
                        for item, embedding in zip(items_batch, embeddings_batch)
                    ]

                    # Upload embeddings to Weaviate
                    upload_batch_to_weaviate(items_with_embeddings_batch)

                    # Set new last update timestamp for the source
                    max_timestamp = last_update
                    batch_max_timestamp = DateTime.instance(
                        items_batch[-1].get(
                            config.EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN
                        )
                    )
                    logger.debug(
                        f"  * '{source}': Batch max timestamp: {batch_max_timestamp}"
                    )
                    logger.debug(
                        f"  * '{source}': Current max timestamp: {max_timestamp}"
                    )
                    if (not max_timestamp) or (batch_max_timestamp > max_timestamp):
                        max_timestamp = batch_max_timestamp
                    if isinstance(max_timestamp, datetime):
                        max_timestamp = DateTime.instance(max_timestamp)
                    set_last_update(last_update=max_timestamp, source_slug=source_slug)
                    logger.info(
                        f"  * '{source}': New last update timestamp set to {max_timestamp}"
                    )

                    # Log progress
                    batches_percentage = batch_number / num_batches * 100
                    logger.info(
                        (
                            f"  * '{source}': {batch_number}/{num_batches}"
                            f" batches processed ({batches_percentage:.2f}%)"
                        )
                    )
            else:
                logger.info(f" * No new reports found for '{source}'.")
    except Exception as exc:
        logger.error(f"Failed to update embeddings: {exc}")
        logger.error(traceback.format_exc())
        send_discord_message(f"Failed to update embeddings: {exc}")
    finally:
        lock.release()
        logger.info("Lock released.")
    logger.info("Finished updating embeddings.")
