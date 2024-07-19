# -*- coding: utf-8 -*-
import asyncio
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
from app.dependencies import get_user
from app.models import MonitoredPlate, NotificationChannel, Operation, User
from app.pydantic_models import (
    CarPassageOut,
    MonitoredPlateIn,
    MonitoredPlateOut,
    MonitoredPlateUpdate,
    Path,
)
from app.utils import get_car_by_radar, get_hints, get_path

router = APIRouter(
    prefix="/cars",
    tags=["Cars"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(
    method="GET",
    router=router,
    path="/hint",
    response_model=list[str],
    responses={
        400: {"description": "At least one of (placa, (start_time, end_time)) must be provided"}
    },
)
async def get_car_hint(
    placa: str,
    start_time: datetime,
    end_time: datetime,
    user: Annotated[User, Depends(get_user)],
    request: Request,
    latitude_min: float = None,
    latitude_max: float = None,
    longitude_min: float = None,
    longitude_max: float = None,
):
    """
    Get plates using the provided hints.
    """
    # Parse start_time and end_time to pendulum.DateTime
    start_time = DateTime.instance(start_time, tz=config.TIMEZONE)
    end_time = DateTime.instance(end_time, tz=config.TIMEZONE)

    # Get hints
    placa = placa.upper()

    # If one of the latitude or longitude is provided, all of them must be provided
    if (
        latitude_min is not None
        or latitude_max is not None
        or longitude_min is not None
        or longitude_max is not None
    ):
        if (
            latitude_min is None
            or latitude_max is None
            or longitude_min is None
            or longitude_max is None
        ):
            raise HTTPException(
                status_code=400,
                detail="If one of the latitude or longitude is provided, all of them must be provided",  # noqa
            )
    hints = await get_hints(
        placa=placa,
        min_datetime=start_time,
        max_datetime=end_time,
        latitude_min=latitude_min,
        latitude_max=latitude_max,
        longitude_min=longitude_min,
        longitude_max=longitude_max,
    )
    return hints


@router_request(method="GET", router=router, path="/path", response_model=list[Path])
async def get_car_path(
    placa: str,
    start_time: datetime,
    end_time: datetime,
    user: Annotated[User, Depends(get_user)],
    request: Request,
    max_time_interval: int = 60 * 60,
    polyline: bool = False,
    min_plate_distance: float = 0,
):
    # Parse start_time and end_time to pendulum.DateTime
    start_time = DateTime.instance(start_time, tz=config.TIMEZONE)
    end_time = DateTime.instance(end_time, tz=config.TIMEZONE)

    # Get path
    placa = placa.upper()
    path = await get_path(
        placa=placa,
        min_datetime=start_time,
        max_datetime=end_time,
        max_time_interval=max_time_interval,
        polyline=polyline,
        min_plate_distance=min_plate_distance,
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
    operation_id: UUID = None,
    operation_title: str = None,
    active: bool = None,
    notification_channel_id: UUID = None,
    notification_channel_title: str = None,
    plate_contains: str = None,
):
    """
    Lists all monitored plates in the system.
    """
    offset = params.size * (params.page - 1)
    monitored_plates_queryset = MonitoredPlate
    filtered = False
    if operation_id:
        filtered = True
        operation = await Operation.get_or_none(id=operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail="Operation not found")
        monitored_plates_queryset = monitored_plates_queryset.filter(operation=operation)
    if operation_title:
        filtered = True
        monitored_plates_queryset = monitored_plates_queryset.filter(
            operation__title__icontains=operation_title
        )
    if active is not None:
        filtered = True
        monitored_plates_queryset = monitored_plates_queryset.filter(active=active)
    if notification_channel_id:
        filtered = True
        notification_channel = await NotificationChannel.get_or_none(id=notification_channel_id)
        if not notification_channel:
            raise HTTPException(status_code=404, detail="Notification channel not found")
        monitored_plates_queryset = monitored_plates_queryset.filter(
            notification_channels=notification_channel
        )
    if notification_channel_title:
        filtered = True
        monitored_plates_queryset = monitored_plates_queryset.filter(
            notification_channels__title__icontains=notification_channel_title
        )
    if plate_contains:
        filtered = True
        monitored_plates_queryset = monitored_plates_queryset.filter(
            plate__icontains=plate_contains
        )
    if not filtered:
        monitored_plates_queryset = monitored_plates_queryset.all()
    monitored_plates_obj = (
        await monitored_plates_queryset.order_by("plate").limit(params.size).offset(offset)
    )
    monitored_plates_awaitables = [
        MonitoredPlateOut.from_monitored_plate(monitored_plate)
        for monitored_plate in monitored_plates_obj
    ]
    monitored_plates = await asyncio.gather(*monitored_plates_awaitables)
    return create_page(
        monitored_plates, params=params, total=await monitored_plates_queryset.count()
    )


@router_request(
    method="POST",
    router=router,
    path="/monitored",
    response_model=MonitoredPlateOut,
    responses={409: {"description": "Plate already monitored"}},
)
async def create_monitored_plate(
    plate_data: MonitoredPlateIn,
    user: Annotated[User, Depends(get_user)],
    request: Request,
):
    """
    Adds a plate to the monitored plates list.
    """
    # Check if plate is already monitored
    if await MonitoredPlate.filter(plate=plate_data.plate).exists():
        raise HTTPException(status_code=409, detail="Plate already monitored")
    # Get operation
    operation = await Operation.get_or_none(id=plate_data.operation_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")
    async with in_transaction():
        monitored_plate = await MonitoredPlate.create(
            operation=operation,
            plate=plate_data.plate,
            active=plate_data.active,
            notes=plate_data.notes,
            additional_info=plate_data.additional_info,
        )
        if plate_data.notification_channels:
            for channel_id in plate_data.notification_channels:
                channel = await NotificationChannel.get_or_none(id=channel_id)
                if not channel:
                    raise HTTPException(status_code=404, detail="Notification channel not found")
                await monitored_plate.notification_channels.add(channel)
    return await MonitoredPlateOut.from_monitored_plate(monitored_plate)


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
    plate = plate.upper()
    monitored_plate = await MonitoredPlate.filter(plate=plate).first()
    if not monitored_plate:
        raise HTTPException(status_code=404, detail="Plate not found")
    return await MonitoredPlateOut.from_monitored_plate(monitored_plate)


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
    user: Annotated[User, Depends(get_user)],
    request: Request,
):
    """
    Updates a monitored plate by its plate number.
    """
    # Check if plate is monitored
    plate = plate.upper()
    monitored_plate = await MonitoredPlate.filter(plate=plate).first()
    if not monitored_plate:
        raise HTTPException(status_code=404, detail="Plate not found")
    async with in_transaction():
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
                            status_code=400,
                            detail="additional_info keys and values must be strings",
                        )
            elif key == "operation_id":
                operation = await Operation.get_or_none(id=value)
                if not operation:
                    raise HTTPException(status_code=404, detail="Operation not found")
                monitored_plate.operation = operation
            elif key == "notification_channels":
                # Notification channels must be a list of UUIDs
                if not isinstance(value, list):
                    raise HTTPException(
                        status_code=400, detail="notification_channels must be a list"
                    )
                # Reset notification channels
                await monitored_plate.notification_channels.clear()
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
    return await MonitoredPlateOut.from_monitored_plate(monitored_plate)


@router_request(
    method="DELETE",
    router=router,
    path="/monitored/{plate}",
    response_model=MonitoredPlateOut,
    responses={404: {"description": "Plate not found"}},
)
async def delete_monitored_plate(
    plate: str,
    user: Annotated[User, Depends(get_user)],
    request: Request,
):
    """
    Removes a plate from the monitored plates list.
    """
    # Check if plate is monitored
    plate = plate.upper()
    monitored_plate = await MonitoredPlate.filter(plate=plate).first()
    if not monitored_plate:
        raise HTTPException(status_code=404, detail="Plate not found")
    await monitored_plate.delete()
    return await MonitoredPlateOut.from_monitored_plate(monitored_plate)


@router_request(method="GET", router=router, path="/radar", response_model=list[CarPassageOut])
async def get_cars_by_radar(
    radar: str,
    start_time: datetime,
    end_time: datetime,
    user: Annotated[User, Depends(get_user)],
    request: Request,
    plate_hint: str = None,
):
    # Parse start_time and end_time to pendulum.DateTime
    start_time = DateTime.instance(start_time, tz=config.TIMEZONE)
    end_time = DateTime.instance(end_time, tz=config.TIMEZONE)

    # Use either camera_numero or codcet
    if radar in config.CODCET_TO_CAMERA_NUMERO:
        codcet = radar
        camera_numero = config.CODCET_TO_CAMERA_NUMERO[codcet]
    else:
        codcet = None
        camera_numero = radar

    return await get_car_by_radar(
        camera_numero=camera_numero,
        codcet=codcet,
        min_datetime=start_time,
        max_datetime=end_time,
        plate_hint=plate_hint,
    )
