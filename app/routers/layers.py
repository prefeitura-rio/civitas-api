# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.decorators import router_request
from app.dependencies import get_user
from app.models import User
from app.utils import get_fogocruzado_reports

router = APIRouter(
    prefix="/layers",
    tags=["Layers"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(method="GET", router=router, path="/fogocruzado", response_model=None)
async def get_shooting_reports(
    user: Annotated[User, Depends(get_user)],
    request: Request,
):
    return await get_fogocruzado_reports()
