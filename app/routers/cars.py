# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pendulum import DateTime

from app import config
from app.decorators import router_get
from app.dependencies import get_user
from app.models import User
from app.pydantic_models import Path
from app.utils import get_path

router = APIRouter(
    prefix="/cars",
    tags=["Cars"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_get(router=router, path="/path", response_model=list[Path])
async def get_car_path(
    placa: str,
    start_time: datetime,
    end_time: datetime,
    user: Annotated[User, Depends(get_user)],
    request: Request,
):
    # Parse start_time and end_time to pendulum.DateTime
    start_time = DateTime.instance(start_time, tz=config.TIMEZONE)
    end_time = DateTime.instance(end_time, tz=config.TIMEZONE)

    # Get path
    path = await get_path(placa, start_time, end_time)

    # Build response
    return [Path(**path_item) for path_item in path]
