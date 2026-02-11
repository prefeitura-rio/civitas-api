# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.utils import get_cameras_cor, get_cameras
from app import config


router = APIRouter(
    prefix="/cameras",
    tags=["Cameras"],
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
    # feature flag to use new cameras service
    # author: Nicolas Evilasio
    # date: 2026-02-11
    # description: This feature flag is used to control the use of the new cameras service.
    # The new cameras service is used to get the cameras list from the BigQuery database merging the cameras from the DC3 and Tixxi systems.
    if config.USE_NEW_CAMERAS_SERVICE:
        return await get_cameras()
    else:
        return await get_cameras_cor()
