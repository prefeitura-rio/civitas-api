# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_pagination import Page, Params
from loguru import logger
from pendulum import DateTime

from app import config
from app.decorators import router_request
from app.dependencies import has_cpf, is_user
from app.models import User
from app.pydantic_models import (
    CarPassageOut,
    CortexCreditsOut,
    CortexPlacaOut,
    CortexPlacasIn,
    GetCarsByRadarIn,
    MonitoredPlateHistory,
    MonitoredPlateIn,
    MonitoredPlateOut,
    MonitoredPlateUpdate,
    NPlatesBeforeAfterOut,
    Path,
)
from app.services import PlateService, BigQueryService, MonitoredPlateService
from app.utils import validate_plate

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
        400: {
            "description": "At least one of (placa, (start_time, end_time)) must be provided"
        }
    },
)
async def get_car_hint(
    placa: str,
    start_time: datetime,
    end_time: datetime,
    user: Annotated[User, Depends(is_user)],
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
    start_time = start_time.in_tz(config.TIMEZONE)
    end_time = DateTime.instance(end_time, tz=config.TIMEZONE)
    end_time = end_time.in_tz(config.TIMEZONE)

    logger.debug(f"Date range: {start_time} - {end_time}")

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
    hints = await BigQueryService.get_vehicle_hints_raw(
        plate=placa,
        start_time=start_time,
        end_time=end_time,
        latitude_min=latitude_min,
        latitude_max=latitude_max,
        longitude_min=longitude_min,
        longitude_max=longitude_max,
    )
    return hints


@router_request(
    method="GET",
    router=router,
    path="/monitored",
    response_model=Page[MonitoredPlateOut],
)
async def get_monitored_plates(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    params: Params = Depends(),
    operation_id: UUID = None,
    operation_title: str = None,
    active: bool = None,
    start_time_create: datetime = None,
    end_time_create: datetime = None,
    notification_channel_id: UUID = None,
    notification_channel_title: str = None,
    plate_contains: str = None,
):
    """
    Lists all monitored plates in the system.
    """
    return await MonitoredPlateService.get_monitored_plates(
        params=params,
        operation_id=operation_id,
        operation_title=operation_title,
        active=active,
        start_time_create=start_time_create,
        end_time_create=end_time_create,
        notification_channel_id=notification_channel_id,
        notification_channel_title=notification_channel_title,
        plate_contains=plate_contains,
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
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Adds a plate to the monitored plates list.
    """
    return await MonitoredPlateService.create_monitored_plate(
        plate_data=plate_data, user=user
    )


@router_request(
    method="GET",
    router=router,
    path="/monitored/history",
    response_model=Page[MonitoredPlateHistory],
)
async def get_monitored_plates_history(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    params: Params = Depends(),
    plate: str = None,
    start_time_create: datetime = None,
    end_time_create: datetime = None,
    start_time_delete: datetime = None,
    end_time_delete: datetime = None,
):
    """
    Get history of monitored plates operations.
    """
    return await MonitoredPlateService.get_monitored_plates_history(
        params=params,
        plate=plate,
        start_time_create=start_time_create,
        end_time_create=end_time_create,
        start_time_delete=start_time_delete,
        end_time_delete=end_time_delete,
    )


@router_request(
    method="GET",
    router=router,
    path="/monitored/{plate}",
    response_model=MonitoredPlateOut,
    responses={404: {"description": "Plate not found"}},
)
async def get_monitored_plate(
    plate: str,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Gets a monitored plate by its plate number.
    """
    return await MonitoredPlateService.get_monitored_plate(plate=plate)


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
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Updates a monitored plate by its plate number.
    """
    return await MonitoredPlateService.update_monitored_plate(
        plate=plate, update_data=plate_data, user=user
    )


@router_request(
    method="DELETE",
    router=router,
    path="/monitored/{plate}",
    response_model=MonitoredPlateOut,
    responses={404: {"description": "Plate not found"}},
)
async def delete_monitored_plate(
    plate: str,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Removes a plate from the monitored plates list.
    """
    # Get the plate before deletion to return it
    monitored_plate_out = await MonitoredPlateService.get_monitored_plate(plate=plate)
    await MonitoredPlateService.delete_monitored_plate(plate=plate, user=user)
    return monitored_plate_out


@router_request(
    method="GET",
    router=router,
    path="/n_before_after",
    response_model=list[NPlatesBeforeAfterOut],
)
async def get_n_plates_before_and_after(
    placa: str,
    start_time: datetime,
    end_time: datetime,
    n_minutes: int,
    user: Annotated[User, Depends(is_user)],
    request: Request,
    n_plates: int = 10,
):
    # Parse start_time and end_time to pendulum.DateTime
    start_time = DateTime.instance(start_time, tz=config.TIMEZONE)
    start_time = start_time.in_tz(config.TIMEZONE)
    end_time = DateTime.instance(end_time, tz=config.TIMEZONE)
    end_time = end_time.in_tz(config.TIMEZONE)

    logger.debug(f"Date range: {start_time} - {end_time}")

    # Get n plates before and after
    placa = placa.upper()
    return BigQueryService.get_plates_before_after_raw(
        plate=placa,
        start_time=start_time,
        end_time=end_time,
        n_minutes=n_minutes,
        n_plates=n_plates,
    )


@router_request(method="GET", router=router, path="/path", response_model=list[Path])
async def get_car_path(
    placa: str,
    start_time: datetime,
    end_time: datetime,
    user: Annotated[User, Depends(is_user)],
    request: Request,
    max_time_interval: int = 60 * 60,
    polyline: bool = False,
):
    # Parse start_time and end_time to pendulum.DateTime
    start_time = DateTime.instance(start_time, tz=config.TIMEZONE)
    start_time = start_time.in_tz(config.TIMEZONE)
    end_time = DateTime.instance(end_time, tz=config.TIMEZONE)
    end_time = end_time.in_tz(config.TIMEZONE)

    logger.debug(f"Date range: {start_time} - {end_time}")

    # Get path
    placa = placa.upper()
    path = await BigQueryService.get_vehicle_path_raw(
        plate=placa,
        start_time=start_time,
        end_time=end_time,
        max_time_interval=max_time_interval,
        polyline=polyline,
    )

    # Build response
    return [Path(**path_item) for path_item in path]


@router_request(
    method="GET",
    router=router,
    path="/plate/{plate}",
    response_model=CortexPlacaOut | None,
    responses={
        400: {"detail": "Invalid plate format"},
        451: {"detail": "Unavailable for legal reasons. CPF might be blocked."},
    },
)
async def get_plate_details(
    plate: str,
    user: Annotated[User, Depends(has_cpf)],
    request: Request,
):
    # Use the new PlateService instead of utils function
    return await PlateService.get_plate_details(plate=plate, cpf=user.cpf)


@router_request(
    method="POST",
    router=router,
    path="/plates",
    response_model=List[CortexPlacaOut | None],
)
async def get_multiple_plates_details(
    plates: CortexPlacasIn,
    user: Annotated[User, Depends(has_cpf)],
    request: Request,
):
    # Use the new PlateService for batch processing
    return await PlateService.get_multiple_plates_details(
        plates=plates.plates, 
        cpf=user.cpf, 
        raise_for_errors=plates.raise_for_errors
    )


@router_request(
    method="POST",
    router=router,
    path="/plates/credit",
    response_model=CortexCreditsOut,
)
async def get_necessary_credits(
    plates: CortexPlacasIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    # Use the new PlateService for credit calculation
    credits_needed = await PlateService.calculate_credits_needed(plates.plates)
    return CortexCreditsOut(credits=credits_needed)


@router_request(
    method="GET", router=router, path="/radar", response_model=list[CarPassageOut]
)
async def get_cars_by_radar(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    data: Annotated[GetCarsByRadarIn, Depends()],
):
    # Parse start_time and end_time to pendulum.DateTime
    start_time = DateTime.instance(data.start_time, tz=config.TIMEZONE)
    start_time = start_time.in_tz(config.TIMEZONE)
    end_time = DateTime.instance(data.end_time, tz=config.TIMEZONE)
    end_time = end_time.in_tz(config.TIMEZONE)

    logger.debug(f"Date range: {start_time} - {end_time}")

    return await BigQueryService.get_cars_by_radar_raw(
        radar_id=data.codcet,
        start_time=start_time,
        end_time=end_time,
        plate_hint=data.plate_hint,
    )
