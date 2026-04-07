# -*- coding: utf-8 -*-
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.modules.tickets.application.dtos import (
    IslandCreateIn,
    TicketCatalogUpdateIn,
    IslandOut,
    IslandPageOut,
)
from app.modules.tickets.application.services.island_service import (
    create_island,
    delete_island,
    get_island_by_id,
    list_islands,
    list_islands_by_team,
    update_island,
)

router = APIRouter(prefix="/islands", tags=["Islands"])


@router_request(
    method="POST",
    router=router,
    path="/",
    response_model=IslandOut,
)
async def create_island_endpoint(
    data: IslandCreateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await create_island(data=data)


@router_request(
    method="GET",
    router=router,
    path="/",
    response_model=IslandPageOut,
)
async def list_islands_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    search: Optional[str] = Query(default=None),
    isActive: Optional[bool] = Query(default=None),
):
    return await list_islands(
        search=search,
        is_active=isActive,
    )


@router_request(
    method="GET",
    router=router,
    path="/team/{team_id}",
    response_model=IslandPageOut,
)
async def list_islands_by_team_endpoint(
    team_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
    search: Optional[str] = Query(default=None),
    isActive: Optional[bool] = Query(default=None),
):
    return await list_islands_by_team(
        team_id=str(team_id),
        search=search,
        is_active=isActive,
    )


@router_request(
    method="GET",
    router=router,
    path="/{island_id}",
    response_model=IslandOut,
)
async def get_island_endpoint(
    island_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await get_island_by_id(island_id=str(island_id))


@router_request(
    method="PUT",
    router=router,
    path="/{island_id}",
    response_model=IslandOut,
)
async def update_island_endpoint(
    island_id: UUID,
    data: TicketCatalogUpdateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await update_island(
        island_id=str(island_id),
        data=data,
    )


@router_request(
    method="DELETE",
    router=router,
    path="/{island_id}",
    response_model=None,
)
async def delete_island_endpoint(
    island_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    await delete_island(island_id=str(island_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)