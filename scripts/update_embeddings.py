# -*- coding: utf-8 -*-
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pytz
import requests
from google.cloud.bigquery.table import Row
from loguru import logger
from pendulum import DateTime
from redis import Redis
from redis.lock import Lock

from app import config
from app.pydantic_models import SearchOutItem
from app.utils import generate_embeddings_batch, get_bigquery_client

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
    return json.dumps(item)


def get_last_update(redis_client: Redis = None) -> DateTime:
    """
    Get the last update timestamp from Redis.

    Args:
        redis_client (Redis, optional): A Redis client. Defaults to None.

    Returns:
        DateTime: The last update timestamp.
    """
    redis = redis_client or get_redis_client()
    val: bytes = redis.get(EMBEDDINGS_LAST_UPDATE_KEY)
    last_update = float(val.decode()) if val else None
    return (
        DateTime.fromtimestamp(last_update, tz=pytz.timezone(config.TIMEZONE))
        if last_update
        else None
    )


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


def get_reports_since_last_update(last_update: DateTime) -> Tuple[List[SearchOutItem], DateTime]:
    """
    Get reports since the last update timestamp.

    Args:
        last_update (DateTime): The last update timestamp.

    Returns:
        Tuple[List[SearchOutItem], DateTime]: A list of reports and the new last update timestamp.
    """
    client = get_bigquery_client()
    query = f"""
        SELECT *
        FROM {config.EMBEDDINGS_SOURCE_TABLE}
    """
    if last_update:
        query += f"""
        WHERE {config.EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN} >
            DATETIME(TIMESTAMP('{last_update}'))
        """
    query_job = client.query(query)
    data = query_job.result(page_size=config.GOOGLE_BIGQUERY_PAGE_SIZE)
    reports = []
    max_timestamp = last_update
    for page in data.pages:
        for row in page:
            row: Row
            timestamp = row.get(config.EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN)
            if (not max_timestamp) or (timestamp > max_timestamp):
                max_timestamp = timestamp
            reports.append(SearchOutItem(**row))
    # Convert max_timestamp to pendulum.DateTime
    if isinstance(max_timestamp, datetime):
        max_timestamp = DateTime.instance(max_timestamp)
    return reports, max_timestamp


def set_last_update(last_update: DateTime, redis_client: Redis = None):
    """
    Set the last update timestamp in Redis.

    Args:
        last_update (DateTime): The last update timestamp.
        redis_client (Redis, optional): A Redis client. Defaults to None.
    """
    redis = redis_client or get_redis_client()
    redis.set(EMBEDDINGS_LAST_UPDATE_KEY, last_update.timestamp())


def upload_batch_to_weaviate(items: List[Dict[str, Any]]):
    """
    Upload a batch of items to Weaviate.

    Args:
        items (List[Dict[str, Any]]): A list of items to upload.
    """
    data_objects = []
    for item in items:
        timestamp: datetime = item[config.EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN]
        timestamp_formatted = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        item[config.EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN] = timestamp_formatted
        item_properties = {k: v for k, v in item.items() if k != "embedding"}
        data_object = {
            "class": "Ocorrencia",
            "id": item[config.EMBEDDINGS_SOURCE_TABLE_ID_COLUMN],
            "properties": item_properties,
            "vector": item["embedding"],
        }
        data_objects.append(data_object)
    response = requests.post(
        f"{config.WEAVIATE_BASE_URL}/v1/batch/objects",
        json={"fields": ["ALL"], "objects": data_objects},
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        logger.error(f"Failed to upload embeddings to Weaviate: {exc}")
        logger.error(response.text)
        raise
    data = response.json()
    for result in data:
        if "errors" in result["result"]:
            raise Exception(result["result"]["errors"])


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
        # Get reports since last update
        last_update = get_last_update()
        if last_update:
            logger.info(f"Last data timestamp was {last_update}")
        else:
            logger.info("No last data timestamp found.")
        reports, new_last_update = get_reports_since_last_update(last_update)
        logger.info(f"Found {len(reports)} reports since {last_update}")
        if len(reports) > 0:
            logger.info(f"New last data timestamp is {new_last_update}")
            # Get embeddings for reports
            logger.info("Getting embeddings for reports...")
            items = [item.dict() for item in reports]
            texts = [generate_text_for_embedding(item) for item in items]
            embeddings = asyncio.run(generate_embeddings_batch(texts))
            items_with_embeddings = [
                {**item, "embedding": embedding} for item, embedding in zip(items, embeddings)
            ]
            # Upload embeddings to Weaviate
            logger.info("Uploading embeddings to Weaviate...")
            upload_batch_to_weaviate(items_with_embeddings)
            logger.info("Embeddings uploaded to Weaviate.")
            # Set new last update timestamp
            logger.info("Setting new last data timestamp...")
            set_last_update(new_last_update)
            logger.info("New last data timestamp set.")
        else:
            logger.info("No new reports found.")
    finally:
        lock.release()
        logger.info("Lock released.")
    logger.info("Finished updating embeddings.")
