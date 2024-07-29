# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page

from app.decorators import router_request
from app.dependencies import is_user, is_admin
from app.models import User, UserHistory
from app.pydantic_models import UserHistoryOut, UserOut

router = APIRouter(
    prefix="/users",
    tags=["User management"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(method="GET", router=router, path="", response_model=Page[UserOut])
async def list_users(
    user: Annotated[User, Depends(is_admin)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all users in the system.
    """
    offset = params.size * (params.page - 1)
    users_obj = await User.all().order_by("username").limit(params.size).offset(offset)
    users = [UserOut.from_orm(user) for user in users_obj]
    return create_page(users, params=params, total=await User.all().count())


@router_request(
    method="GET",
    router=router,
    path="/history",
    response_model=Page[UserHistoryOut],
    responses={
        404: {"description": "User not found"},
    },
)
async def get_full_history(
    request: Request,
    user: Annotated[User, Depends(is_admin)],
    params: Params = Depends(),
    method: Optional[str] = None,
    path: Optional[str] = None,
    status_code: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Page[UserHistoryOut]:
    """
    Get user history by ID
    """
    offset = params.size * (params.page - 1)
    history_query = UserHistory
    filtered = False
    if method:
        method = method.upper()
        history_query = history_query.filter(method=method)
        filtered = True
    if path:
        path = path.lower()
        history_query = history_query.filter(path=path)
        filtered = True
    if status_code:
        history_query = history_query.filter(status_code=status_code)
        filtered = True
    if start_time:
        history_query = history_query.filter(timestamp__gte=start_time)
        filtered = True
    if end_time:
        history_query = history_query.filter(timestamp__lte=end_time)
        filtered = True
    if not filtered:
        history_query = history_query.all()
    history_obj = await history_query.order_by("timestamp").limit(params.size).offset(offset)
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
    return create_page(history, params=params, total=await history_query.count())


@router_request(
    method="GET",
    router=router,
    path="/me",
    response_model=UserOut,
)
async def get_me(request: Request, user: User = Depends(get_user)) -> UserOut:
    """
    Get the current user
    """
    return UserOut.from_orm(user)


@router_request(
    method="GET",
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


@router_request(
    method="GET",
    router=router,
    path="/{user_id}/history",
    response_model=Page[UserHistoryOut],
    responses={
        404: {"description": "User not found"},
    },
)
async def get_user_history(
    request: Request,
    user_id: UUID,
    user: Annotated[User, Depends(is_admin)],
    params: Params = Depends(),
    method: Optional[str] = None,
    path: Optional[str] = None,
    status_code: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Page[UserHistoryOut]:
    """
    Get user history by ID
    """
    user_obj = await User.get_or_none(id=user_id)
    if not user_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    offset = params.size * (params.page - 1)
    history_query = UserHistory.filter(user=user_obj)
    if method:
        method = method.upper()
        history_query = history_query.filter(method=method)
    if path:
        path = path.lower()
        history_query = history_query.filter(path=path)
    if status_code:
        history_query = history_query.filter(status_code=status_code)
    if start_time:
        history_query = history_query.filter(timestamp__gte=start_time)
    if end_time:
        history_query = history_query.filter(timestamp__lte=end_time)
    history_obj = await history_query.order_by("timestamp").limit(params.size).offset(offset)
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
    return create_page(history, params=params, total=await history_query.count())
