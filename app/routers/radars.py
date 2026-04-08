# -*- coding: utf-8 -*-
from typing import Annotated, List

from fastapi import APIRouter, Depends, Request

from app import config
from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.pydantic_models import LprCollectionPointOut, RadarOut
from app.utils import get_lpr_collection_points_positions, get_radar_positions

router = APIRouter(
    prefix="/radars",
    tags=["Radars"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)

# feature flag to enable new radar list endpoint
# author: Nicolas Evilasio
# date: 2026-04-08
# description: This feature flag is used to control the use of the new radar list endpoint.
# The new radar list endpoint is used to get the radar positions from the LPR collection points instead of the old radar list endpoint.
if config.ENABLE_NEW_RADAR_LIST_ENDPOINT:
    response_model = list[LprCollectionPointOut]
    function = get_lpr_collection_points_positions
else:
    response_model = list[RadarOut]
    function = get_radar_positions


@router_request(method="GET", router=router, path="", response_model=response_model)
async def get_radars_list(
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await function()
