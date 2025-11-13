
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
from app.utils import generate_download_signed_url
from app.pydantic_models import (
    GCSDownloadIn,
    GCSDownloadOut,
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
