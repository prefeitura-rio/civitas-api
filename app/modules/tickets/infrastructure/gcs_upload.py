# app/utils/gcs_upload.py
# -*- coding: utf-8 -*-
import asyncio
import uuid
from typing import Optional

from fastapi import HTTPException
from google.cloud.exceptions import NotFound, Forbidden
from google.api_core import exceptions as google_exceptions
from loguru import logger

from app.utils import get_storage_client


async def gcs_upload_file_bytes(
    *,
    bucket_name: str,
    object_name: str,
    content: bytes,
    content_type: Optional[str] = None,
) -> dict:
    """
    Faz upload direto para GCS.
    Retorna metadados básicos do objeto.
    """

    def _upload():
        try:
            storage_client = get_storage_client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(object_name)

            blob.upload_from_string(
                content,
                content_type=content_type,
                timeout=60,
            )

            blob.reload()
            return {
                "bucket": bucket_name,
                "name": blob.name,
                "size": blob.size or len(content),
                "content_type": blob.content_type,
                "crc32c": blob.crc32c,
                "md5_hash": blob.md5_hash,
                "updated": blob.updated,
                "etag": blob.etag,
            }

        except NotFound:
            logger.warning(f"Bucket '{bucket_name}' not found or access denied")
            raise HTTPException(
                status_code=403,
                detail="Access denied to this resource. Check your permissions.",
            )
        except Forbidden:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to bucket '{bucket_name}'. Check your permissions.",
            )
        except google_exceptions.GoogleAPIError as e:
            logger.exception(f"Google Cloud Storage API error uploading file: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file to GCS. Please try again later.",
            )
        except Exception as e:
            logger.exception(f"Unexpected error uploading file to GCS: {e}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while uploading the file",
            )

    return await asyncio.to_thread(_upload)


async def gcs_delete_object(
    *,
    bucket_name: str,
    object_name: str,
) -> None:
    """
    Remove um objeto do GCS.
    Idempotente: se não existir, apenas loga e segue.
    """

    def _delete():
        try:
            storage_client = get_storage_client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.delete(timeout=30)

        except NotFound:
            logger.warning(
                f"GCS object not found during compensation: "
                f"bucket='{bucket_name}', object='{object_name}'"
            )
        except Forbidden:
            logger.exception(
                f"Access denied deleting GCS object during compensation: "
                f"bucket='{bucket_name}', object='{object_name}'"
            )
            raise
        except google_exceptions.GoogleAPIError as e:
            logger.exception(
                f"Google Cloud Storage API error deleting file '{object_name}': {e}"
            )
            raise
        except Exception as e:
            logger.exception(
                f"Unexpected error deleting GCS object '{object_name}': {e}"
            )
            raise

    await asyncio.to_thread(_delete)


async def gcs_delete_objects(
    *,
    bucket_name: str,
    object_names: list[str],
) -> None:
    """
    Melhor esforço para apagar vários objetos.
    Não interrompe na primeira falha.
    """
    if not object_names:
        return

    results = await asyncio.gather(
        *[
            gcs_delete_object(bucket_name=bucket_name, object_name=object_name)
            for object_name in object_names
        ],
        return_exceptions=True,
    )

    for object_name, result in zip(object_names, results):
        if isinstance(result, Exception):
            logger.exception(
                f"Failed to compensate GCS object deletion: "
                f"bucket='{bucket_name}', object='{object_name}', error='{result}'"
            )

async def gcs_download_file_bytes(
    *,
    bucket_name: str,
    object_name: str,
) -> bytes:
    def _download():
        try:
            storage_client = get_storage_client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(object_name)

            return blob.download_as_bytes(timeout=60)

        except NotFound:
            raise HTTPException(
                status_code=404,
                detail="Arquivo não encontrado no storage.",
            )
        except Forbidden:
            raise HTTPException(
                status_code=403,
                detail="Acesso negado ao arquivo.",
            )
        except google_exceptions.GoogleAPIError:
            raise HTTPException(
                status_code=500,
                detail="Falha ao baixar arquivo do GCS.",
            )
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Erro inesperado ao baixar arquivo.",
            )

    return await asyncio.to_thread(_download)


def build_ticket_object_name(ticket_id: str, original_filename: str) -> str:
    safe_name = (original_filename or "file").replace("/", "_").replace("\\", "_")
    return f"tickets/{ticket_id}/{uuid.uuid4()}-{safe_name}"

def build_email_attachment_object_name(email_id: str, original_filename: str) -> str:
    safe_name = (original_filename or "file").replace("/", "_").replace("\\", "_")
    return f"emails/{email_id}/attachments/{uuid.uuid4()}-{safe_name}"