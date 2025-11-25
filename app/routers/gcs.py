
import asyncio
import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from google.cloud.exceptions import NotFound, Forbidden
from google.api_core import exceptions as google_exceptions
from loguru import logger
from app.dependencies import is_user
from app.models import User
from app.utils import check_file_exists, gcs_delete_file, generate_download_signed_url, generate_upload_signed_url, list_blobs
from app.pydantic_models import (
    GCSDeleteFileIn,
    GCSDownloadIn,
    GCSDownloadOut,
    GCSFileExistsIn,
    GCSFileExistsOut,
    GCSFileInfoOut,
    GCSUploadIn,
    GCSUploadOut,
    ListFilesIn,
)
from app.decorators import router_request


router = APIRouter(
    prefix="/gcs",
    tags=["GCS"],
    responses={
        400: {"description": "Bad request. Invalid parameters provided."},
        401: {"description": "You don't have permission to do this."},
        403: {"description": "Access denied to bucket or file. Check your permissions."},
        429: {"error": "Rate limit exceeded"},
        500: {"description": "Internal server error. An unexpected error occurred."},
    },
)


@router_request(method="GET", router=router, path="/files", response_model=Page[GCSFileInfoOut])
async def list_files(
    request: Request,
    user: Annotated[User, Depends(is_user)],
    data: ListFilesIn = Depends(),
    params: Params = Depends(),
):
    """
    Lists all files in the specified bucket with pagination and sorting.
    """
    offset = params.size * (params.page - 1)
    files, total = await list_blobs(
        bucket_name=data.bucket_name,
        order_by=data.order_by,
        limit=params.size,
        offset=offset,
    )
    return create_page(files, params=params, total=total)


@router_request(method="GET", router=router, path="/files/exists", response_model=GCSFileExistsOut)
async def check_file_exists_endpoint(
    request: Request,
    user: Annotated[User, Depends(is_user)],
    data: GCSFileExistsIn = Depends(),
):
    """
    Checks if a file with the given name already exists in the bucket.
    """
    exists = await check_file_exists(data.file_name, data.bucket_name)
    return GCSFileExistsOut(
        exists=exists, file_name=data.file_name, bucket_name=data.bucket_name
    )


@router_request(method="POST", router=router, path="/upload-url", response_model=GCSUploadOut)
async def get_gcs_upload_signed_url(
    request: Request,
    user: Annotated[User, Depends(is_user)],
    data: GCSUploadIn,
):
    """
    Provides a signed URL to allow direct file upload to Google Cloud Storage.
    Also returns whether a file with the same name already exists.

    **How to upload the file:**

    1. Call this endpoint to get a signed URL
    2. Use the returned URL to upload your file directly to GCS (not to this API):

    **If resumable = True:**
    - PUT request to the signed URL (session already started)
    - Headers: `Content-Type` (matching file type), `Content-Length` (file size)

    **If resumable = False:**
    - PUT request to the signed URL (session not started)
    - Headers: `Content-Type` (must exactly match the `content_type` provided)
    """
    file_exists, signed_url = await asyncio.gather(
        check_file_exists(data.file_name, data.bucket_name),
        generate_upload_signed_url(
            file_name=data.file_name,
            content_type=data.content_type,
            bucket_name=data.bucket_name,
            file_size=data.file_size,
            resumable=data.resumable,
            origin=request.headers.get("Origin", None),
            file_path=data.file_path,
        ),
    )
    return GCSUploadOut(signed_url=signed_url, file_exists=file_exists)


@router_request(method="POST", router=router, path="/files/download-url", response_model=GCSDownloadOut)
async def get_gcs_download_signed_url(
    request: Request,
    user: Annotated[User, Depends(is_user)],
    data: GCSDownloadIn,
):
    """
    Provides a signed URL to allow direct file download from Google Cloud Storage.
    """
    download_url = await generate_download_signed_url(
        file_name=data.file_name,
        bucket_name=data.bucket_name,
        expiration_minutes=data.expiration_minutes,
    )
    return GCSDownloadOut(
        download_url=download_url,
        expires_in_seconds=data.expiration_minutes * 60,
    )


@router_request(method="DELETE", router=router, path="/files", response_model=dict)
async def delete_file(
    request: Request,
    user: Annotated[User, Depends(is_user)],
    data: GCSDeleteFileIn,
):
    """
    Deletes a file from the specified bucket.
    
    Raises:
        HTTPException: If bucket or file is not found, access is forbidden, or deletion fails.
    """
    return await gcs_delete_file(file_name=data.file_name, bucket_name=data.bucket_name)
