# -*- coding: utf-8 -*-
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.modules.tickets.application.dtos import (
    TicketCatalogCreateIn,
    TicketCatalogUpdateIn,
    TicketTypeListItemOut,
    TicketTypeOut,
)
from app.modules.tickets.application.services.ticket_type_service import (
    create_ticket_type,
    delete_ticket_type,
    get_ticket_type_by_id,
    list_ticket_types,
    update_ticket_type,
)

router = APIRouter(prefix="/ticket-types", tags=["Ticket Types"])


@router_request(
    method="POST",
    router=router,
    path="/",
    response_model=TicketTypeOut,
)
async def create_ticket_type_endpoint(
    data: TicketCatalogCreateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await create_ticket_type(data=data)


@router_request(
    method="GET",
    router=router,
    path="/",
    response_model=List[TicketTypeListItemOut],
)
async def list_ticket_types_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    search: Optional[str] = Query(default=None),
    isActive: Optional[bool] = Query(default=None),
):
    return await list_ticket_types(
        search=search,
        is_active=isActive,
    )


@router_request(
    method="GET",
    router=router,
    path="/{ticket_type_id}",
    response_model=TicketTypeOut,
)
async def get_ticket_type_endpoint(
    ticket_type_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await get_ticket_type_by_id(ticket_type_id=str(ticket_type_id))


@router_request(
    method="PUT",
    router=router,
    path="/{ticket_type_id}",
    response_model=TicketTypeOut,
)
async def update_ticket_type_endpoint(
    ticket_type_id: UUID,
    data: TicketCatalogUpdateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await update_ticket_type(
        ticket_type_id=str(ticket_type_id),
        data=data,
    )


@router_request(
    method="DELETE",
    router=router,
    path="/{ticket_type_id}",
    response_model=None,
)
async def delete_ticket_type_endpoint(
    ticket_type_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    await delete_ticket_type(ticket_type_id=str(ticket_type_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)