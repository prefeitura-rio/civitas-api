# app/routers/tickets.py
# -*- coding: utf-8 -*-
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, Query, UploadFile

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.modules.tickets.application.dtos import TicketCreateResultOut, TicketDashboardFilterIn, TicketDashboardOut, TicketOut, TicketSearchOut
from app.modules.tickets.application.services.ticket_service import convert_ticket_to_conventional, create_ticket, get_ticket_by_id, get_tickets_dashboard, parse_ticket_payload, search_tickets


router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router_request(
    method="POST",
    router=router,
    path="/dashboard",
    response_model=TicketDashboardOut,
)
async def get_tickets_dashboard_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    filters: TicketDashboardFilterIn,
):
    return await get_tickets_dashboard(
        user=user,
        filters=filters,
    )


@router.post("/", response_model=TicketCreateResultOut)
async def create_ticket_endpoint(
    payload: Annotated[str, Form(...)],
    files: Annotated[Optional[List[UploadFile]], File()] = None,
    user: Annotated[User, Depends(is_user)] = None,
    request: Request = None,
):
    ticket_in = parse_ticket_payload(payload)
    return await create_ticket(ticket_in=ticket_in, author=user, files=files or [])


@router.get("/search", response_model=List[TicketSearchOut])
async def search_tickets_endpoint(
    search: str = Query(..., min_length=1, description="Texto para buscar tickets"),
):
    return await search_tickets(search=search)


@router.post("/{ticket_id}/convert-to-conventional", response_model=bool)
async def convert_ticket_to_conventional_endpoint(
    ticket_id: UUID,
    files: Annotated[Optional[List[UploadFile]], File()] = None,
    email_id: Optional[UUID] = Query(default=None),
    user: Annotated[User, Depends(is_user)] = None,
    request: Request = None,
):
    return await convert_ticket_to_conventional(
        ticket_id=str(ticket_id),
        files=files or [],
        email_id=str(email_id) if email_id else None,
    )


@router_request(
    method="GET",
    router=router,
    path="/{ticket_id}",
    response_model=TicketOut,
)
async def get_ticket_endpoint(
    ticket_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await get_ticket_by_id(ticket_id=ticket_id)

