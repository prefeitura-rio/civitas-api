# -*- coding: utf-8 -*-
from typing import Annotated, List

from fastapi import APIRouter, Depends, Request

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.pydantic_models import WazeAlertOut
from app.utils import get_waze_alerts, normalize_waze_alerts

router = APIRouter(
    prefix="/waze",
    tags=["Waze"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(method="GET", router=router, path="/police", response_model=List[WazeAlertOut])
async def get_waze_police_alerts(
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    alerts = await get_waze_alerts("POLICE")
    return normalize_waze_alerts(alerts)
