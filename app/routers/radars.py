# -*- coding: utf-8 -*-
from typing import Annotated, List

from fastapi import APIRouter, Depends, Request

from app.decorators import router_request
from app.dependencies import get_user
from app.models import User
from app.pydantic_models import RadarOut
from app.utils import get_radar_positions

router = APIRouter(
    prefix="/radars",
    tags=["Radars"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(method="GET", router=router, path="", response_model=List[RadarOut])
async def get_radars_list(
    user: Annotated[User, Depends(get_user)],
    request: Request,
):
    return await get_radar_positions()
