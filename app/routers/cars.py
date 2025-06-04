# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from loguru import logger
from pendulum import DateTime
from tortoise.transactions import in_transaction

from app import config
from app.decorators import router_request
from app.dependencies import has_cpf, is_user
from app.models import (
    MonitoredPlate,
    NotificationChannel,
    Operation,
    PlateData,
    User,
)
from app.pydantic_models import (
    CarPassageOut,
    CortexCreditsOut,
    CortexPlacaOut,
    CortexPlacasIn,
    MonitoredPlateHistory,
    MonitoredPlateIn,
    MonitoredPlateOut,
    MonitoredPlateUpdate,
    NPlatesBeforeAfterOut,
    Path,
)
from app.utils import (
    get_car_by_radar,
    get_hints,
    get_path,
    get_n_plates_before_and_after as utils_get_n_plates_before_and_after,
)
from app.utils import get_plate_details as utils_get_plate_details
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
    offset = params.size * (params.page - 1)
    monitored_plates_queryset = MonitoredPlate
    filtered = False
    if operation_id:
        filtered = True
        operation = await Operation.get_or_none(id=operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail="Operation not found")
        monitored_plates_queryset = monitored_plates_queryset.filter(
            operation=operation
        )
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
        notification_channel = await NotificationChannel.get_or_none(
            id=notification_channel_id
        )
        if not notification_channel:
            raise HTTPException(
                status_code=404, detail="Notification channel not found"
            )
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
    if start_time_create and end_time_create:
        filtered = True
        monitored_plates_queryset = monitored_plates_queryset.filter(
            created_at__gte=start_time_create, created_at__lte=end_time_create
        )
    if not filtered:
        monitored_plates_queryset = monitored_plates_queryset.all()
    monitored_plates_obj = (
        await monitored_plates_queryset.order_by("plate")
        .limit(params.size)
        .offset(offset)
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
    user: Annotated[User, Depends(is_user)],
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
            contact_info=plate_data.contact_info,
            notes=plate_data.notes,
            additional_info=plate_data.additional_info,
        )
        if plate_data.notification_channels:
            for channel_id in plate_data.notification_channels:
                channel = await NotificationChannel.get_or_none(id=channel_id)
                if not channel:
                    raise HTTPException(
                        status_code=404, detail="Notification channel not found"
                    )
                await monitored_plate.notification_channels.add(channel)
    return await MonitoredPlateOut.from_monitored_plate(monitored_plate)


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
    # Parse start_time and end_time to pendulum.DateTime
    if start_time_create:
        start_time_create = DateTime.instance(start_time_create, tz=config.TIMEZONE)
        start_time_create = start_time_create.in_tz(config.TIMEZONE)
    else:
        start_time_create = DateTime(1970, 1, 1)
    if end_time_create:
        end_time_create = DateTime.instance(end_time_create, tz=config.TIMEZONE)
        end_time_create = end_time_create.in_tz(config.TIMEZONE)
    else:
        end_time_create = DateTime.now(tz=config.TIMEZONE)
    if start_time_delete:
        start_time_delete = DateTime.instance(start_time_delete, tz=config.TIMEZONE)
        start_time_delete = start_time_delete.in_tz(config.TIMEZONE)
    else:
        start_time_delete = DateTime(1970, 1, 1)
    if end_time_delete:
        end_time_delete = DateTime.instance(end_time_delete, tz=config.TIMEZONE)
        end_time_delete = end_time_delete.in_tz(config.TIMEZONE)
    else:
        end_time_delete = DateTime.now(tz=config.TIMEZONE)

    plate_filter = ""
    if plate:
        plate_filter = " AND (add_history.plate = $7 OR del_history.plate = $7)"

    offset = (params.page - 1) * params.size
    query = f"""
    WITH plate_adding_history AS (
        SELECT
            body->>'plate' AS plate,
            body->>'notes' AS notes,
            timestamp AS created_timestamp,
            user_id::text AS created_by
        FROM userhistory
        WHERE path = '/cars/monitored'
            AND status_code >= 200
            AND status_code < 300
            AND method = 'POST'
            AND timestamp >= $1
            AND timestamp <= $2
    ),
    plate_deleting_history AS (
        SELECT
            reverse(split_part(reverse(path), '/'::text, 1)) AS plate,
            timestamp AS deleted_timestamp,
            user_id::text AS deleted_by
        FROM userhistory
        WHERE path LIKE '/cars/monitored/%'
            AND status_code >= 200
            AND status_code < 300
            AND method = 'DELETE'
            AND timestamp >= $3
            AND timestamp <= $4
    ),
    final_history AS (
        SELECT
            COALESCE(add_history.plate, del_history.plate) AS plate,
            add_history.created_timestamp,
            add_history.created_by,
            del_history.deleted_timestamp,
            del_history.deleted_by,
            add_history.notes
        FROM plate_adding_history add_history
        FULL OUTER JOIN plate_deleting_history del_history
        ON add_history.plate = del_history.plate
        WHERE TRUE {plate_filter}  -- Dynamic plate filter if needed
        ORDER BY COALESCE(add_history.created_timestamp, del_history.deleted_timestamp) DESC
    )
    SELECT
        *,
        COUNT(*) OVER() AS total
    FROM final_history
    OFFSET $5
    LIMIT $6;
    """
    # Execute raw SQL query using Tortoise-ORM
    async with in_transaction() as conn:
        logger.debug(f"Connection: {conn}")
        args = [
            start_time_create,
            end_time_create,
            start_time_delete,
            end_time_delete,
            offset,
            params.size,
        ]
        if plate:
            args.append(plate)
        _, results = await conn.execute_query(query, args)
        total = results[0]["total"]
        logger.debug(f"Results: {results}")

    # Format results into dict
    user_ids = set()
    for result in results:
        if result["created_by"]:
            user_ids.add(result["created_by"])
        if result["deleted_by"]:
            user_ids.add(result["deleted_by"])
    user_ids = list(user_ids)
    user_awaitables = [User.get_or_none(id=user_id) for user_id in user_ids]
    users = await asyncio.gather(*user_awaitables)
    users_dict = {str(user.id): user for user in users}
    plates = [
        {
            "plate": result["plate"],
            "created_timestamp": result["created_timestamp"],
            "created_by": users_dict[result["created_by"]]
            if result["created_by"]
            else None,
            "deleted_timestamp": result["deleted_timestamp"],
            "deleted_by": users_dict[result["deleted_by"]]
            if result["deleted_by"]
            else None,
            "notes": result["notes"],
        }
        for result in results
    ]

    return create_page(
        [MonitoredPlateHistory(**plate) for plate in plates],
        params=params,
        total=total,
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
    user: Annotated[User, Depends(is_user)],
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
                    raise HTTPException(
                        status_code=400, detail="additional_info must be a dict"
                    )
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
                            status_code=400,
                            detail="notification_channels must be a list of UUIDs",
                        )
                    channel = await NotificationChannel.get_or_none(id=channel_id)
                    if not channel:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Notification channel '{channel_id}' not found",
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
    user: Annotated[User, Depends(is_user)],
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
    return utils_get_n_plates_before_and_after(
        placa=placa,
        min_datetime=start_time,
        max_datetime=end_time,
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
    min_plate_distance: float = 0,
):
    # Parse start_time and end_time to pendulum.DateTime
    start_time = DateTime.instance(start_time, tz=config.TIMEZONE)
    start_time = start_time.in_tz(config.TIMEZONE)
    end_time = DateTime.instance(end_time, tz=config.TIMEZONE)
    end_time = end_time.in_tz(config.TIMEZONE)

    logger.debug(f"Date range: {start_time} - {end_time}")

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
    # Validate plate
    plate = plate.upper()
    if not validate_plate(plate):
        raise HTTPException(status_code=400, detail="Invalid plate format")

    # Get plate details
    return await utils_get_plate_details(plate=plate, cpf=user.cpf)


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
    # Validate plates
    for plate in plates.plates:
        plate = plate.upper()
        if not validate_plate(plate):
            raise HTTPException(
                status_code=400, detail=f"Invalid plate format: {plate}"
            )

    # Get plates from our database
    plates_list = plates.plates

    # Await for all plates in batches of 10
    plates_details = []
    for i in range(0, len(plates_list), 10):
        plates_details += await asyncio.gather(
            *[
                utils_get_plate_details(
                    plate=plate, cpf=user.cpf, raise_for_errors=plates.raise_for_errors
                )
                for plate in plates_list[i : i + 10]
            ]
        )

    return plates_details


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
    # Check, using the provided list of plates, how many aren't in our database
    plates_data = await PlateData.filter(plate__in=plates.plates).values_list(
        "plate", flat=True
    )
    missing_plates = list(set(plates.plates) - set(plates_data))
    return CortexCreditsOut(credits=len(missing_plates))


@router_request(
    method="GET", router=router, path="/radar", response_model=list[CarPassageOut]
)
async def get_cars_by_radar(
    radar: str,
    start_time: datetime,
    end_time: datetime,
    user: Annotated[User, Depends(is_user)],
    request: Request,
    plate_hint: str = None,
):
    # Parse start_time and end_time to pendulum.DateTime
    start_time = DateTime.instance(start_time, tz=config.TIMEZONE)
    start_time = start_time.in_tz(config.TIMEZONE)
    end_time = DateTime.instance(end_time, tz=config.TIMEZONE)
    end_time = end_time.in_tz(config.TIMEZONE)

    logger.debug(f"Date range: {start_time} - {end_time}")

    # # Use either camera_numero or codcet
    if len(radar.replace("-", "").strip()) >= 9:
        codcet = radar.zfill(10)
        camera_numero = [c_num for c_num, codc in config.CAMERA_NUMERO_TO_CODCET.items() if codc == codcet]
        
        if camera_numero:
            camera_numero = "', '".join(camera_numero)
    else:
        camera_numero = radar
        codcet = config.CAMERA_NUMERO_TO_CODCET.get(camera_numero, None)

    logger.debug(f"Camera numero: {camera_numero}, CODCET: {codcet}")

    return await get_car_by_radar(
        camera_numero=camera_numero,
        codcet=codcet,
        min_datetime=start_time,
        max_datetime=end_time,
        plate_hint=plate_hint,
    )
