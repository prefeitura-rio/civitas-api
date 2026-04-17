# -*- coding: utf-8 -*-
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.modules.tickets.application.dtos import (
    UserRoleListItemOut,
    UserRoleOut,
    UserRolePageOut,
    UserRoleUpdateIn,
)
from app.modules.tickets.application.services.user_service import (
    get_user_roles_by_id,
    list_users_only_with_roles,
    list_users_with_roles,
    update_user_roles,
)

router = APIRouter(
    prefix="/users-roles",
    tags=["User Roles Management"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)

@router_request(
    method="GET",
    router=router,
    path="/",
    response_model=UserRolePageOut,
)
async def list_users_with_roles_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(
        default=None,
        min_length=1,
        description="Texto para buscar usuários (nome, e-mail ou usuário)",
    ),
):
    return await list_users_with_roles(
        page=page,
        page_size=page_size,
        search=search,
    )


@router_request(
    method="GET",
    router=router,
    path="/assigned",
    response_model=list[UserRoleListItemOut],
)
async def list_users_only_with_roles_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await list_users_only_with_roles()




@router_request(
    method="GET",
    router=router,
    path="/{user_id}",
    response_model=UserRoleOut,
)
async def get_user_roles_by_id_endpoint(
    user_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await get_user_roles_by_id(
        user_id=str(user_id),
    )


@router_request(
    method="PUT",
    router=router,
    path="/{user_id}",
    response_model=UserRoleOut,
)
async def update_user_roles_endpoint(
    user_id: UUID,
    data: UserRoleUpdateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await update_user_roles(
        user_id=str(user_id),
        data=data,
    )