# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from tortoise.exceptions import ValidationError

from app.decorators import router_request
from app.dependencies import is_user
from app.models import NotificationChannel, User
from app.pydantic_models import (
    NotificationChannelIn,
    NotificationChannelOut,
    NotificationChannelUpdate,
)

router = APIRouter(
    prefix="/notification-channels",
    tags=["Notification channels"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(
    method="GET", router=router, path="", response_model=Page[NotificationChannelOut]
)
async def get_notification_channels(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all notification channels in the system.
    """
    offset = params.size * (params.page - 1)
    notification_channels_obj = (
        await NotificationChannel.all()
        .order_by("title")
        .limit(params.size)
        .offset(offset)
    )
    notification_channels = [
        NotificationChannelOut.from_orm(monitored_plate)
        for monitored_plate in notification_channels_obj
    ]
    return create_page(
        notification_channels,
        params=params,
        total=await NotificationChannel.all().count(),
    )


@router_request(
    method="POST", router=router, path="", response_model=NotificationChannelOut
)
async def create_notification_channel(
    notification_channel: NotificationChannelIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Creates a new notification channel.
    """
    try:
        notification_channel_obj = await NotificationChannel.create(
            **notification_channel.dict()
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return NotificationChannelOut.from_orm(notification_channel_obj)


@router_request(
    method="GET",
    router=router,
    path="/{notification_channel_id}",
    response_model=NotificationChannelOut,
)
async def get_notification_channel(
    notification_channel_id: str,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Retrieves a notification channel by its ID.
    """
    notification_channel_obj = await NotificationChannel.get_or_none(
        id=notification_channel_id
    )
    if not notification_channel_obj:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    return NotificationChannelOut.from_orm(notification_channel_obj)


@router_request(
    method="PUT",
    router=router,
    path="/{notification_channel_id}",
    response_model=NotificationChannelOut,
)
async def update_notification_channel(
    notification_channel_id: str,
    notification_channel_data: NotificationChannelUpdate,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Updates a notification channel.
    """
    notification_channel_obj = await NotificationChannel.get_or_none(
        id=notification_channel_id
    )
    if not notification_channel_obj:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    for key, value in notification_channel_data.dict().items():
        if value is None:
            continue
        setattr(notification_channel_obj, key, value)
    await notification_channel_obj.save()
    return NotificationChannelOut.from_orm(notification_channel_obj)


@router_request(
    method="DELETE",
    router=router,
    path="/{notification_channel_id}",
    response_model=NotificationChannelOut,
)
async def delete_notification_channel(
    notification_channel_id: str,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Deletes a notification channel.
    """
    notification_channel_obj = await NotificationChannel.get_or_none(
        id=notification_channel_id
    )
    if not notification_channel_obj:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    await notification_channel_obj.delete()
    return NotificationChannelOut.from_orm(notification_channel_obj)
