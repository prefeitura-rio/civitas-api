# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from app import config
from app.decorators import router_request
from app.dependencies import has_cpf
from app.models import PlateData, User
from app.pydantic_models import CortexPlacaOut
from app.utils import cortex_request, validate_plate

router = APIRouter(
    prefix="/cortex",
    tags=["Cortex"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(
    method="GET",
    router=router,
    path="/plate/{plate}",
    response_model=CortexPlacaOut,
    responses={400: {"detail": "Invalid plate format"}},
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

    # Check if we already have this plate in our database
    plate_data = await PlateData.get_or_none(plate=plate)

    # If we do, return it
    if plate_data:
        logger.debug(f"Found plate {plate} in our database. Returning cached data.")
        return CortexPlacaOut(**plate_data.data)

    # If we don't, try to fetch it from Cortex
    logger.debug(f"Plate {plate} not found in our database. Fetching data from Cortex.")
    data = await cortex_request(
        method="GET",
        url=f"{config.CORTEX_VEICULOS_BASE_URL}/emplacamentos/placa/{plate}",
        cpf=user.cpf,
    )

    # Save the data to our database
    await PlateData.create(plate=plate, data=data)
    return CortexPlacaOut(**data)
