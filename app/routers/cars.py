# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from pendulum import DateTime
from tortoise.transactions import in_transaction

from app import config
from app.decorators import router_request
from app.dependencies import get_user, is_admin
from app.models import MonitoredPlate, NotificationChannel, User
from app.pydantic_models import (
    MonitoredPlateIn,
    MonitoredPlateOut,
    MonitoredPlateUpdate,
    Path,
)
from app.utils import get_path

router = APIRouter(
    prefix="/cars",
    tags=["Cars"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(method="GET", router=router, path="/path", response_model=list[Path])
async def get_car_path(
    placa: str,
    start_time: datetime,
    end_time: datetime,
    user: Annotated[User, Depends(get_user)],
    request: Request,
    max_time_interval: int = 60 * 60,
    polyline: bool = False,
):
    # Parse start_time and end_time to pendulum.DateTime
    start_time = DateTime.instance(start_time, tz=config.TIMEZONE)
    end_time = DateTime.instance(end_time, tz=config.TIMEZONE)

    # Get path
    path = await get_path(
        placa=placa,
        min_datetime=start_time,
        max_datetime=end_time,
        max_time_interval=max_time_interval,
        polyline=polyline,
    )

    # Build response
    return [Path(**path_item) for path_item in path]


@router_request(
    method="GET", router=router, path="/monitored", response_model=Page[MonitoredPlateOut]
)
async def get_monitored_plates(
    user: Annotated[User, Depends(get_user)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all monitored plates in the system.
    """
    offset = params.size * (params.page - 1)
    monitored_plates_obj = await MonitoredPlate.all().limit(params.size).offset(offset)
    monitored_plates = [
        MonitoredPlateOut(**await monitored_plate.to_dict())
        for monitored_plate in monitored_plates_obj
    ]
    return create_page(monitored_plates, params=params, total=await MonitoredPlate.all().count())


@router_request(
    method="POST",
    router=router,
    path="/monitored",
    response_model=MonitoredPlateOut,
    responses={409: {"description": "Plate already monitored"}},
)
async def create_monitored_plate(
    plate_data: MonitoredPlateIn,
    user: Annotated[User, Depends(is_admin)],
    request: Request,
):
    """
    Adds a plate to the monitored plates list.
    """
    # Check if plate is already monitored
    if await MonitoredPlate.filter(plate=plate_data.plate).exists():
        raise HTTPException(status_code=409, detail="Plate already monitored")
    async with in_transaction():
        monitored_plate = await MonitoredPlate.create(
            **plate_data.dict(exclude={"notification_channels"})
        )
        if plate_data.notification_channels:
            for channel_id in plate_data.notification_channels:
                channel = await NotificationChannel.get_or_none(id=channel_id)
                if not channel:
                    raise HTTPException(status_code=404, detail="Notification channel not found")
                await monitored_plate.notification_channels.add(channel)
    return MonitoredPlateOut(**await monitored_plate.to_dict())


@router_request(
    method="GET",
    router=router,
    path="/monitored/{plate}",
    response_model=MonitoredPlateOut,
    responses={404: {"description": "Plate not found"}},
)
async def get_monitored_plate(
    plate: str,
    user: Annotated[User, Depends(get_user)],
    request: Request,
):
    """
    Gets a monitored plate by its plate number.
    """
    # Check if plate is monitored
    monitored_plate = await MonitoredPlate.filter(plate=plate).first()
    if not monitored_plate:
        raise HTTPException(status_code=404, detail="Plate not found")
    return MonitoredPlateOut(**await monitored_plate.to_dict())


@router_request(
    method="PUT",
    router=router,
    path="/monitored/{plate}",
    response_model=MonitoredPlateOut,
    responses={404: {"description": "Plate not found"}},
)
async def update_monitored_plate(
    plate: str,
    plate_data: MonitoredPlateUpdate,
    user: Annotated[User, Depends(is_admin)],
    request: Request,
):
    """
    Updates a monitored plate by its plate number.
    """
    # Check if plate is monitored
    monitored_plate = await MonitoredPlate.filter(plate=plate).first()
    if not monitored_plate:
        raise HTTPException(status_code=404, detail="Plate not found")
    for key, value in plate_data.dict().items():
        if value is None:
            continue
        if key == "additional_info":
            # Additional info must be a Dict[str, str]
            if not isinstance(value, dict):
                raise HTTPException(status_code=400, detail="additional_info must be a dict")
            for k, v in value.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise HTTPException(
                        status_code=400, detail="additional_info keys and values must be strings"
                    )
        elif key == "notification_channels":
            # Notification channels must be a list of UUIDs
            if not isinstance(value, list):
                raise HTTPException(status_code=400, detail="notification_channels must be a list")
            for channel_id in value:
                if not isinstance(channel_id, UUID):
                    raise HTTPException(
                        status_code=400, detail="notification_channels must be a list of UUIDs"
                    )
                channel = await NotificationChannel.get_or_none(id=channel_id)
                if not channel:
                    raise HTTPException(
                        status_code=404, detail=f"Notification channel '{channel_id}' not found"
                    )
                await monitored_plate.notification_channels.add(channel)
            continue
        setattr(monitored_plate, key, value)
    await monitored_plate.save()
    return MonitoredPlateOut(**await monitored_plate.to_dict())


@router_request(
    method="DELETE",
    router=router,
    path="/monitored/{plate}",
    response_model=MonitoredPlateOut,
    responses={404: {"description": "Plate not found"}},
)
async def delete_monitored_plate(
    plate: str,
    user: Annotated[User, Depends(is_admin)],
    request: Request,
):
    """
    Removes a plate from the monitored plates list.
    """
    # Check if plate is monitored
    monitored_plate = await MonitoredPlate.filter(plate=plate).first()
    if not monitored_plate:
        raise HTTPException(status_code=404, detail="Plate not found")
    await monitored_plate.delete()
    return MonitoredPlateOut(**await monitored_plate.to_dict())
