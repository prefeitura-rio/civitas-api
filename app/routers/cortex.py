# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app import config
from app.decorators import router_request
from app.dependencies import has_cpf
from app.models import User
from app.pydantic_models import CortexPlacaOut
from app.utils import cortex_request

router = APIRouter(
    prefix="/cortex",
    tags=["Cortex"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(method="GET", router=router, path="/plate/{plate}", response_model=CortexPlacaOut)
async def get_plate_details(
    plate: str,
    user: Annotated[User, Depends(has_cpf)],
    request: Request,
):
    data = await cortex_request(
        method="GET",
        url=f"{config.CORTEX_VEICULOS_BASE_URL}/emplacamentos/placa/{plate}",
        cpf=user.cpf,
    )
    return CortexPlacaOut(**data)
