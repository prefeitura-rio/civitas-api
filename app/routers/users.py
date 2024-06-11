# -*- coding: utf-8 -*-
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page

from app import config
from app.decorators import router_get
from app.dependencies import get_user, is_admin
from app.models import User, UserHistory
from app.pydantic_models import UserHistoryOut, UserOut
from app.rate_limiter import limiter

router = APIRouter(
    prefix="/users",
    tags=["User management"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_get(router=router, path="", response_model=Page[UserOut])
async def list_users(
    user: Annotated[User, Depends(is_admin)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all users in the system.
    """
    offset = params.size * (params.page - 1)
    users_obj = await User.all().limit(params.size).offset(offset)
    users = [UserOut.from_orm(user) for user in users_obj]
    return create_page(users, params=params, total=await User.all().count())


@router_get(
    router=router,
    path="/me",
    response_model=UserOut,
)
async def get_me(request: Request, user: User = Depends(get_user)) -> UserOut:
    """
    Get the current user
    """
    return UserOut.from_orm(user)


@router_get(
    router=router,
    path="/{user_id}",
    response_model=UserOut,
    responses={
        404: {"description": "User not found"},
    },
)
async def get_user_by_id(
    request: Request, user_id: UUID, user: Annotated[User, Depends(is_admin)]
) -> UserOut:
    """
    Get user by ID
    """
    user_obj = await User.get_or_none(id=user_id)
    if not user_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut.from_orm(user_obj)


@router_get(
    router=router,
    path="/{user_id}/history",
    response_model=Page[UserHistoryOut],
    responses={
        404: {"description": "User not found"},
    },
)
@limiter.limit(config.RATE_LIMIT_DEFAULT)
async def get_user_history(
    request: Request,
    user_id: UUID,
    user: Annotated[User, Depends(is_admin)],
    params: Params = Depends(),
) -> Page[UserHistoryOut]:
    """
    Get user history by ID
    """
    user_obj = await User.get_or_none(id=user_id)
    if not user_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    offset = params.size * (params.page - 1)
    history_obj = await UserHistory.filter(user=user_obj).limit(params.size).offset(offset)
    history = [
        UserHistoryOut(
            id=history.id,
            method=history.method,
            path=history.path,
            query_params=history.query_params,
            body=history.body,
            status_code=history.status_code,
            timestamp=history.timestamp,
        )
        for history in history_obj
    ]
    return create_page(
        history, params=params, total=await UserHistory.filter(user=user_obj).count()
    )
