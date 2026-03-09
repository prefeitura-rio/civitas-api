# -*- coding: utf-8 -*-
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.modules.tickets.application.dtos import (
    TicketCatalogCreateIn,
    TicketCatalogUpdateIn,
    TicketNatureOut,
    TicketNaturePageOut,
)
from app.modules.tickets.application.services.ticket_nature_service import (
    create_ticket_nature,
    delete_ticket_nature,
    get_ticket_nature_by_id,
    list_ticket_natures,
    update_ticket_nature,
)

router = APIRouter(prefix="/ticket-natures", tags=["Ticket Natures"])


@router_request(
    method="POST",
    router=router,
    path="/",
    response_model=TicketNatureOut,
)
async def create_ticket_nature_endpoint(
    data: TicketCatalogCreateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await create_ticket_nature(data=data)


@router_request(
    method="GET",
    router=router,
    path="/",
    response_model=TicketNaturePageOut,
)
async def list_ticket_natures_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    search: Optional[str] = Query(default=None),
    isActive: Optional[bool] = Query(default=None),
):
    return await list_ticket_natures(
        search=search,
        is_active=isActive,
    )


@router_request(
    method="GET",
    router=router,
    path="/{nature_id}",
    response_model=TicketNatureOut,
)
async def get_ticket_nature_endpoint(
    nature_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await get_ticket_nature_by_id(nature_id=str(nature_id))


@router_request(
    method="PUT",
    router=router,
    path="/{nature_id}",
    response_model=TicketNatureOut,
)
async def update_ticket_nature_endpoint(
    nature_id: UUID,
    data: TicketCatalogUpdateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await update_ticket_nature(
        nature_id=str(nature_id),
        data=data,
    )


@router.delete(
    "/{nature_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_ticket_nature_endpoint(
    nature_id: UUID,
    user: Annotated[User, Depends(is_user)],
):
    await delete_ticket_nature(nature_id=str(nature_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)