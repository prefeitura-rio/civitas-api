# -*- coding: utf-8 -*-
import traceback
from typing import Annotated

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from app import config
from app.decorators import router_request
from app.dependencies import is_user
from app.models import User

router = APIRouter(
    prefix="/cameras-cor",
    tags=["COR Cameras"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(method="GET", router=router, path="", response_model=None)
async def get_cameras_list(
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
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
